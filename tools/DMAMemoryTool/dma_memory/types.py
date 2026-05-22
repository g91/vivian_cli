"""
dma_memory.types — Data type and scan type definitions.

Handles encoding/decoding between Python values and raw bytes for all
supported types: int8/16/32/64, uint variants, float32, float64,
UTF-8/UTF-16 strings, and raw byte arrays.
"""
from __future__ import annotations

import struct
from enum import Enum, auto
from typing import Any, Optional


class DataType(Enum):
    """Supported value types for memory scanning."""
    INT8    = "int8"
    INT16   = "int16"
    INT32   = "int32"
    INT64   = "int64"
    UINT8   = "uint8"
    UINT16  = "uint16"
    UINT32  = "uint32"
    UINT64  = "uint64"
    FLOAT   = "float"    # 32-bit IEEE 754
    DOUBLE  = "double"   # 64-bit IEEE 754
    STRING_UTF8  = "string_utf8"
    STRING_UTF16 = "string_utf16"
    BYTES   = "bytes"    # raw byte array / AoB


class ScanType(Enum):
    """How the scan value is compared against memory."""
    EXACT       = auto()  # value == target
    NOT_EQUAL   = auto()  # value != target
    GREATER     = auto()  # value >  target
    LESS        = auto()  # value <  target
    RANGE       = auto()  # min <= value <= max  (pass (min, max) as value)
    CHANGED     = auto()  # value != previous (next_scan only)
    UNCHANGED   = auto()  # value == previous (next_scan only)
    INCREASED   = auto()  # value >  previous (next_scan only)
    DECREASED   = auto()  # value <  previous (next_scan only)
    INCREASED_BY = auto() # value == previous + target
    DECREASED_BY = auto() # value == previous - target
    UNKNOWN     = auto()  # first scan — store all readable addresses


# ── Format strings ────────────────────────────────────────────────────────────

_FMT: dict[DataType, str] = {
    DataType.INT8:   "<b",
    DataType.INT16:  "<h",
    DataType.INT32:  "<i",
    DataType.INT64:  "<q",
    DataType.UINT8:  "<B",
    DataType.UINT16: "<H",
    DataType.UINT32: "<I",
    DataType.UINT64: "<Q",
    DataType.FLOAT:  "<f",
    DataType.DOUBLE: "<d",
}


def type_size(dt: DataType) -> int:
    """Return the byte size of a numeric DataType."""
    fmt = _FMT.get(dt)
    if fmt is None:
        raise ValueError(f"type_size() not applicable to {dt}")
    return struct.calcsize(fmt)


def encode(value: Any, dt: DataType) -> bytes:
    """Encode a Python value to bytes for the given DataType."""
    fmt = _FMT.get(dt)
    if fmt:
        return struct.pack(fmt, value)
    if dt == DataType.STRING_UTF8:
        return value.encode("utf-8")
    if dt == DataType.STRING_UTF16:
        return value.encode("utf-16-le")
    if dt == DataType.BYTES:
        if isinstance(value, (bytes, bytearray)):
            return bytes(value)
        # Accept space-separated hex string
        return bytes(int(b, 16) for b in value.split())
    raise ValueError(f"Cannot encode type {dt}")


def decode(raw: bytes, dt: DataType) -> Any:
    """Decode raw bytes to a Python value for the given DataType."""
    fmt = _FMT.get(dt)
    if fmt:
        size = struct.calcsize(fmt)
        return struct.unpack(fmt, raw[:size])[0]
    if dt == DataType.STRING_UTF8:
        return raw.split(b"\x00")[0].decode("utf-8", errors="replace")
    if dt == DataType.STRING_UTF16:
        # Find null terminator (two consecutive \x00 on even boundary)
        i = 0
        while i + 1 < len(raw):
            if raw[i] == 0 and raw[i + 1] == 0 and i % 2 == 0:
                break
            i += 2
        return raw[:i].decode("utf-16-le", errors="replace")
    if dt == DataType.BYTES:
        return raw
    raise ValueError(f"Cannot decode type {dt}")


def format_value(value: Any, dt: DataType) -> str:
    """Human-readable representation of a value."""
    if dt in (DataType.FLOAT, DataType.DOUBLE):
        return f"{value:.6g}"
    if dt in (DataType.STRING_UTF8, DataType.STRING_UTF16):
        return repr(value)
    if dt == DataType.BYTES:
        return " ".join(f"{b:02X}" for b in value)
    return str(value)


def compare(value: Any, prev: Any, target: Any, scan_type: ScanType,
            target2: Optional[Any] = None) -> bool:
    """Return True if the comparison passes."""
    if scan_type == ScanType.EXACT:
        if isinstance(target, float):
            return abs(value - target) < 1e-4
        return value == target
    if scan_type == ScanType.NOT_EQUAL:
        return value != target
    if scan_type == ScanType.GREATER:
        return value > target
    if scan_type == ScanType.LESS:
        return value < target
    if scan_type == ScanType.RANGE:
        lo, hi = target, target2
        return lo <= value <= hi
    if scan_type == ScanType.CHANGED:
        return value != prev
    if scan_type == ScanType.UNCHANGED:
        return value == prev
    if scan_type == ScanType.INCREASED:
        return value > prev
    if scan_type == ScanType.DECREASED:
        return value < prev
    if scan_type == ScanType.INCREASED_BY:
        return abs(value - (prev + target)) < 1e-4
    if scan_type == ScanType.DECREASED_BY:
        return abs(value - (prev - target)) < 1e-4
    if scan_type == ScanType.UNKNOWN:
        return True
    return False
