"""reader.py — UE3 memory reader + pattern scanner for UESDKGen.

UE3Reader    — dumps GNames / GObjects, detects name offset, scans for TArrays.
PatternScanner — scans a memory range for a byte pattern+mask, returns the
                 dereferenced VA written at (match + offset).
"""
from __future__ import annotations

import struct
from typing import Dict, List, Optional, Tuple

try:
    from .backends import MemoryBackend
except ImportError:
    from backends import MemoryBackend  # type: ignore[no-redef]


# ─────────────────────────────────────────────────────────────────────────────
# Pattern scanner
# ─────────────────────────────────────────────────────────────────────────────

class PatternScanner:
    """Scan a memory region for a byte pattern with wildcard mask.

    mask chars:
      'x'  — byte must equal the pattern byte
      '?'  — any byte (wildcard)

    After finding a match the scanner reads a pointer at (match_va + rel_off)
    and returns that VA — mimicking the classic GObjects/GNames scan-and-deref
    used in UE3 injectors.
    """

    _CHUNK = 0x10000  # 64 KB read chunks

    def __init__(self, backend: MemoryBackend) -> None:
        self._backend = backend

    # public ──────────────────────────────────────────────────────────────────

    def scan(self, base: int, size: int,
             pattern: bytes, mask: str, rel_off: int = 0,
             is64: bool = False) -> Optional[int]:
        """Return the dereferenced pointer at the first pattern match, or None."""
        overlap = len(pattern) - 1
        end     = base + size
        pos     = base
        while pos < end:
            read_size = min(self._CHUNK, end - pos + overlap)
            data      = self._backend.read(pos, read_size)
            if not data:
                pos += self._CHUNK
                continue
            idx = self._match(data, pattern, mask)
            if idx is not None:
                match_va = pos + idx
                return self._backend.rptr(match_va + rel_off, is64)
            pos += self._CHUNK - overlap
        return None

    # private ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _match(data: bytes, pattern: bytes, mask: str) -> Optional[int]:
        plen = len(pattern)
        for i in range(len(data) - plen + 1):
            if all(mask[j] == "?" or data[i + j] == pattern[j]
                   for j in range(plen)):
                return i
        return None


# ─────────────────────────────────────────────────────────────────────────────
# UE3 memory reader
# ─────────────────────────────────────────────────────────────────────────────

class UE3Reader:
    """Back-end-agnostic UE3 GNames / GObjects reader.

    32-bit UE3 memory layout (from Engine.h / community RE):
      UObject +0x2C  FName.dwIndex   (NAME_FIELD_OFF default)
      FNameEntry +0x10  char Name[]  (NAME_STR_OFF default, ASCII not wchar_t)
    """

    def __init__(self,
                 backend:        MemoryBackend,
                 gobjects_va:    int  = 0x013B9B78,
                 gnames_va:      int  = 0x01377868,
                 name_field_off: int  = 0x2C,
                 name_str_off:   int  = 0x10,
                 name_encoding:  str  = "ascii",
                 is64:           bool = False) -> None:
        self.backend        = backend
        self.gobjects_va    = gobjects_va
        self.gnames_va      = gnames_va
        self.name_field_off = name_field_off
        self.name_str_off   = name_str_off
        self.name_encoding  = name_encoding
        self.is64           = is64
        self.ptr_sz         = 8 if is64 else 4

    # ── low-level helpers ─────────────────────────────────────────────────

    def _tarray(self, va: int) -> Tuple[int, int]:
        """Return (data_ptr, count) for a TArray at va."""
        data  = self.backend.rptr(va, self.is64) or 0
        count = self.backend.ru32(va + self.ptr_sz) or 0
        return data, count

    def _elem_ptr(self, data: int, idx: int) -> Optional[int]:
        return self.backend.rptr(data + idx * self.ptr_sz, self.is64)

    def _read_str(self, va: int, max_chars: int = 512) -> Optional[str]:
        """Read a null-terminated string from va using the profile's encoding."""
        raw = self.backend.read(va, max_chars)
        if not raw:
            return None
        end = raw.find(b"\x00")
        raw = raw[:end] if end >= 0 else raw
        return raw.decode(self.name_encoding, errors="replace")

    # ── public API ────────────────────────────────────────────────────────

    def dump_names(self, cb=None) -> Dict[int, str]:
        """Dump GNames; cb(i, total) called every 500 entries."""
        data, count = self._tarray(self.gnames_va)
        if not data or not count:
            return {}
        out: Dict[int, str] = {}
        for i in range(count):
            ptr = self._elem_ptr(data, i)
            if not ptr:
                continue
            name = self._read_str(ptr + self.name_str_off)
            if name:
                out[i] = name
            if cb and i % 500 == 0:
                cb(i, count)
        return out

    def dump_objects(self, names: Dict[int, str], cb=None) -> List[Dict]:
        """Dump GObjects; cb(i, total) called every 500 entries."""
        data, count = self._tarray(self.gobjects_va)
        if not data or not count:
            return []
        out: List[Dict] = []
        for i in range(count):
            ptr = self._elem_ptr(data, i)
            if not ptr:
                continue
            ni = self.backend.ru32(ptr + self.name_field_off)
            if ni is None:
                continue
            out.append({
                "index":      i,
                "ptr":        ptr,
                "name_index": ni,
                "name":       names.get(ni, f"?{ni}"),
            })
            if cb and i % 500 == 0:
                cb(i, count)
        return out

    def detect_name_offset(self, names: Dict[int, str],
                           sample: int = 100) -> Optional[int]:
        """Heuristic: vote for the DWORD offset most likely to be NameIndex."""
        data, count = self._tarray(self.gobjects_va)
        if not data or not count or not names:
            return None
        valid_ids = set(names.keys())
        offsets   = list(range(0, 0x50, 4))
        votes: Dict[int, int] = {}
        tested = 0
        for i in range(min(count, 2000)):
            ptr = self._elem_ptr(data, i)
            if not ptr:
                continue
            for off in offsets:
                val = self.backend.ru32(ptr + off)
                if val is not None and val in valid_ids and names[val]:
                    votes[off] = votes.get(off, 0) + 1
            tested += 1
            if tested >= sample:
                break
        if not votes:
            return None
        best = max(votes, key=lambda k: votes[k])
        return best if votes[best] >= 3 else None

    def scan_tarrays(self, base: int, length: int, cb=None) -> List[Dict]:
        """Scan a memory range for TArray-shaped triples (data, count, max)."""
        results: List[Dict] = []
        step = self.ptr_sz
        end  = base + length
        for addr in range(base, end, step):
            data_ptr = self.backend.rptr(addr, self.is64)
            if not data_ptr or data_ptr < 0x10000:
                continue
            count = self.backend.ru32(addr + self.ptr_sz)
            max_  = self.backend.ru32(addr + self.ptr_sz + 4)
            if (count is None or max_ is None or
                    count < 64 or count > 600_000 or
                    max_ < count or max_ > 1_000_000):
                continue
            elem0 = self.backend.rptr(data_ptr, self.is64)
            if not elem0 or elem0 < 0x10000:
                continue
            note = ""
            if 30_000 <= count <= 300_000:
                note = "GNames candidate"
            elif 5_000 <= count <= 150_000:
                note = "GObjects candidate"
            results.append({
                "va":       addr,
                "offset":   addr - base,
                "data_ptr": data_ptr,
                "count":    count,
                "max":      max_,
                "note":     note,
            })
            if cb:
                cb(addr - base, length)
            if len(results) >= 256:
                break
        return results
