"""
dma_memory.scanner — Memory scanning engine.

Supports:
- Numeric scans (int8/16/32/64, uint, float, double) with EXACT/RANGE/CHANGED/etc.
- String search (UTF-8 and UTF-16LE)
- Array-of-Bytes (AoB) pattern scan with '?' wildcards
- Unknown-value first scan (stores all readable addresses)
- Pointer chain scanner

Internally reads memory in 1 MB chunks for efficiency.
Optionally uses numpy for accelerated numeric searches.
"""
from __future__ import annotations

import re
import struct
import time
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from .types import (
    DataType, ScanType, encode, decode, compare, type_size,
    format_value,
)
from .results import ScanResults, MatchAddress, _read_size

if TYPE_CHECKING:
    from .process import DMAProcess

# ── Optional numpy ────────────────────────────────────────────────────────────
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

_CHUNK = 1 * 1024 * 1024  # 1 MB per read

# Numeric DataTypes that map to numpy dtypes
_NP_DTYPES: Dict[DataType, str] = {
    DataType.INT8:   "int8",
    DataType.INT16:  "<i2",
    DataType.INT32:  "<i4",
    DataType.INT64:  "<i8",
    DataType.UINT8:  "uint8",
    DataType.UINT16: "<u2",
    DataType.UINT32: "<u4",
    DataType.UINT64: "<u8",
    DataType.FLOAT:  "<f4",
    DataType.DOUBLE: "<f8",
}


class MemoryScanner:
    """
    High-performance memory scanner for a DMAProcess.

    Typical workflow:
        scanner = proc.scanner()
        results = scanner.scan(100.0, DataType.FLOAT)
        # change value in game...
        results = scanner.next_scan(results, 75.0)
        results.print_table()
    """

    def __init__(self, proc: "DMAProcess") -> None:
        self._proc = proc

    # ── Region helpers ────────────────────────────────────────────────────────

    def _readable_regions(
        self,
        only_writable: bool = False,
        skip_image: bool = False,
    ) -> List[Tuple[int, int]]:
        """Return (start, size) tuples for all readable memory regions."""
        regions = self._proc.memory_regions()
        result = []
        for r in regions:
            if skip_image and "image" in r.get("type", "").lower():
                continue
            prot = r.get("protection", "")
            if only_writable and "w" not in prot.lower():
                continue
            start = r["va_start"]
            size  = r["size"]
            if size > 0:
                result.append((start, size))
        return result

    # ── Numeric scan ──────────────────────────────────────────────────────────

    def scan(
        self,
        value: Any,
        data_type: DataType = DataType.INT32,
        scan_type: ScanType = ScanType.EXACT,
        value2: Any = None,               # upper bound for ScanType.RANGE
        only_writable: bool = False,
        skip_image: bool = False,
    ) -> ScanResults:
        """
        First scan — search all readable memory regions.

        Args:
            value:        The value to search for (or lower bound for RANGE).
            data_type:    The type of value (DataType.INT32, FLOAT, etc.).
            scan_type:    How to compare: EXACT, RANGE, GREATER, LESS, UNKNOWN.
            value2:       Upper bound when scan_type == RANGE.
            only_writable: Only scan writable pages.
            skip_image:   Skip image (DLL/EXE) pages.

        Returns:
            ScanResults with all matching addresses.
        """
        if data_type in (DataType.STRING_UTF8, DataType.STRING_UTF16):
            return self.search_string(value, data_type)
        if data_type == DataType.BYTES:
            return self.search_aob(value)

        matches: List[MatchAddress] = []
        regions = self._readable_regions(only_writable, skip_image)
        val_size = type_size(data_type)
        pattern = encode(value, data_type) if scan_type != ScanType.UNKNOWN else None

        for base, region_size in regions:
            matches.extend(
                self._scan_region_numeric(
                    base, region_size, value, pattern,
                    data_type, val_size, scan_type, None, value2,
                )
            )

        return ScanResults(matches, data_type, self._proc)

    def next_scan(
        self,
        results: ScanResults,
        value: Any = None,
        scan_type: ScanType = ScanType.EXACT,
        value2: Any = None,
    ) -> ScanResults:
        """
        Narrow down a previous ScanResults.

        For relative types (CHANGED, INCREASED, etc.) the stored values are
        used as the baseline — value may be None.
        """
        return results.next_scan(value, scan_type, value2)

    def _scan_region_numeric(
        self,
        base: int,
        region_size: int,
        target: Any,
        pattern: Optional[bytes],
        data_type: DataType,
        val_size: int,
        scan_type: ScanType,
        prev_map: Optional[Dict[int, Any]],
        target2: Any,
    ) -> List[MatchAddress]:
        """Scan a single memory region for numeric values."""
        if HAS_NUMPY and scan_type in (ScanType.EXACT, ScanType.RANGE,
                                        ScanType.GREATER, ScanType.LESS,
                                        ScanType.UNKNOWN):
            return self._scan_region_numpy(
                base, region_size, target, data_type, scan_type, target2
            )
        return self._scan_region_struct(
            base, region_size, target, val_size, data_type, scan_type, prev_map, target2
        )

    def _scan_region_numpy(
        self,
        base: int,
        region_size: int,
        target: Any,
        data_type: DataType,
        scan_type: ScanType,
        target2: Any,
    ) -> List[MatchAddress]:
        """NumPy-accelerated scan."""
        np_dtype = _NP_DTYPES.get(data_type)
        if np_dtype is None:
            return []

        matches = []
        val_size = type_size(data_type)
        offset = 0

        while offset < region_size:
            chunk_size = min(_CHUNK, region_size - offset)
            # Round down to val_size multiple
            chunk_size = (chunk_size // val_size) * val_size
            if chunk_size == 0:
                break

            raw = self._proc.read(base + offset, chunk_size)
            if not raw or len(raw) < val_size:
                offset += _CHUNK
                continue

            # Trim to multiple of val_size
            trim = (len(raw) // val_size) * val_size
            arr = np.frombuffer(raw[:trim], dtype=np.dtype(np_dtype))

            if scan_type == ScanType.EXACT:
                if data_type in (DataType.FLOAT, DataType.DOUBLE):
                    idxs = np.where(np.abs(arr.astype(np.float64) - float(target)) < 1e-4)[0]
                else:
                    idxs = np.where(arr == target)[0]
            elif scan_type == ScanType.GREATER:
                idxs = np.where(arr > target)[0]
            elif scan_type == ScanType.LESS:
                idxs = np.where(arr < target)[0]
            elif scan_type == ScanType.RANGE:
                idxs = np.where((arr >= target) & (arr <= target2))[0]
            else:  # UNKNOWN
                idxs = np.arange(len(arr))

            for idx in idxs:
                addr = base + offset + int(idx) * val_size
                val  = arr[idx].item()
                matches.append(MatchAddress(addr, val, data_type, self._proc))

            offset += chunk_size

        return matches

    def _scan_region_struct(
        self,
        base: int,
        region_size: int,
        target: Any,
        val_size: int,
        data_type: DataType,
        scan_type: ScanType,
        prev_map: Optional[Dict[int, Any]],
        target2: Any,
    ) -> List[MatchAddress]:
        """Pure-Python struct-based scan (fallback without numpy)."""
        fmt_map = {
            DataType.INT8: "<b", DataType.INT16: "<h",
            DataType.INT32: "<i", DataType.INT64: "<q",
            DataType.UINT8: "<B", DataType.UINT16: "<H",
            DataType.UINT32: "<I", DataType.UINT64: "<Q",
            DataType.FLOAT: "<f", DataType.DOUBLE: "<d",
        }
        fmt = fmt_map.get(data_type)
        if fmt is None:
            return []

        matches = []
        offset = 0
        while offset < region_size:
            chunk_size = min(_CHUNK, region_size - offset)
            raw = self._proc.read(base + offset, chunk_size)
            if not raw:
                offset += _CHUNK
                continue

            i = 0
            while i + val_size <= len(raw):
                try:
                    val = struct.unpack_from(fmt, raw, i)[0]
                    addr = base + offset + i
                    prev = prev_map.get(addr) if prev_map else None
                    if compare(val, prev, target, scan_type, target2):
                        matches.append(MatchAddress(addr, val, data_type, self._proc, prev))
                except struct.error:
                    pass
                i += val_size
            offset += chunk_size

        return matches

    # ── String search ─────────────────────────────────────────────────────────

    def search_string(
        self,
        text: str,
        data_type: DataType = DataType.STRING_UTF16,
        only_writable: bool = False,
    ) -> ScanResults:
        """
        Search for a string (UTF-8 or UTF-16LE) in all readable memory.

        Args:
            text:      The string to find.
            data_type: STRING_UTF8 or STRING_UTF16 (default: UTF-16 for Windows).
        """
        if data_type == DataType.STRING_UTF8:
            pattern = text.encode("utf-8")
        else:
            pattern = text.encode("utf-16-le")
            data_type = DataType.STRING_UTF16

        matches: List[MatchAddress] = []
        regions = self._readable_regions(only_writable)

        for base, region_size in regions:
            offset = 0
            while offset < region_size:
                chunk_size = min(_CHUNK, region_size - offset)
                raw = self._proc.read(base + offset, chunk_size)
                if not raw:
                    offset += _CHUNK
                    continue

                pos = 0
                while True:
                    idx = raw.find(pattern, pos)
                    if idx == -1:
                        break
                    addr = base + offset + idx
                    matches.append(MatchAddress(addr, text, data_type, self._proc))
                    pos = idx + 1

                # Slide back by len(pattern)-1 to catch splits across chunks
                offset += chunk_size - (len(pattern) - 1)
                offset = max(offset, base + len(pattern))  # sanity
                offset = offset  # keep going

        return ScanResults(matches, data_type, self._proc)

    # ── AoB / pattern scan ────────────────────────────────────────────────────

    def search_aob(
        self,
        pattern: "str | bytes",
        only_writable: bool = False,
    ) -> ScanResults:
        """
        Array-of-Bytes scan with optional '?' wildcards.

        Pattern format (space-separated hex):
            "48 8B 05 ? ? ? ? 48 8B"   ← '?' matches any single byte
            "48 8B 05 ?? ?? ?? ?? 48"  ← '??' also works
            b"\\x48\\x8B\\x05"         ← raw bytes (no wildcards)

        Returns ScanResults with DataType.BYTES.
        """
        if isinstance(pattern, bytes):
            # Exact bytes — use fast find
            regex = re.compile(re.escape(pattern), re.DOTALL)
            pat_len = len(pattern)
        else:
            regex, pat_len = _compile_aob(pattern)

        matches: List[MatchAddress] = []
        regions = self._readable_regions(only_writable)

        for base, region_size in regions:
            offset = 0
            while offset < region_size:
                chunk_size = min(_CHUNK, region_size - offset)
                raw = self._proc.read(base + offset, chunk_size)
                if not raw:
                    offset += _CHUNK
                    continue

                for m in regex.finditer(raw):
                    addr = base + offset + m.start()
                    val  = bytes(raw[m.start():m.start() + pat_len])
                    matches.append(MatchAddress(addr, val, DataType.BYTES, self._proc))

                offset += chunk_size - (pat_len - 1)

        return ScanResults(matches, DataType.BYTES, self._proc)

    # ── Pointer scanner ───────────────────────────────────────────────────────

    def find_pointers_to(
        self,
        target_address: int,
        alignment: int = 8,
        only_writable: bool = False,
    ) -> List[int]:
        """
        Find all addresses that contain target_address as a pointer value.

        Useful for finding a stable pointer chain to a dynamic address.
        """
        # Encode as little-endian 8-byte pointer
        target_bytes = struct.pack("<Q", target_address)
        results = self.search_aob(target_bytes, only_writable)
        # Filter by alignment
        return [
            m.address for m in results
            if m.address % alignment == 0
        ]

    def scan_pointer_chain(
        self,
        base: int,
        offsets: List[int],
        is_64bit: bool = True,
    ) -> Optional[int]:
        """
        Resolve a pointer chain and return the final address.
        Returns None if any pointer in the chain is invalid.
        """
        return self._proc.resolve_pointer_chain(base, offsets, is_64bit)


# ── AoB pattern compiler ──────────────────────────────────────────────────────

def _compile_aob(pattern: str):
    """
    Compile a space-separated hex pattern with '?' wildcards into a
    (compiled_regex, pattern_byte_length) tuple.

    Examples:
        "48 8B 05 ? ? ? ? 48"   → matches 8 bytes, middle 4 are wildcards
        "E8 ?? ?? ?? ?? 90"     → matches 6 bytes
    """
    parts = pattern.strip().split()
    regex_parts = []
    length = 0
    for part in parts:
        part = part.strip()
        if part in ("?", "??"):
            regex_parts.append(b".")
        elif len(part) == 2:
            try:
                b = int(part, 16)
                regex_parts.append(re.escape(bytes([b])))
            except ValueError:
                raise ValueError(f"Invalid byte in AoB pattern: {part!r}")
        else:
            raise ValueError(f"Invalid token in AoB pattern: {part!r}")
        length += 1
    return re.compile(b"".join(regex_parts), re.DOTALL), length
