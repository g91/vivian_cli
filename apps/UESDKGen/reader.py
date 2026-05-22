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

    def scan_rip(self, base: int, size: int,
                pattern: bytes, mask: str, rel_off: int = 0,
                adjust: int = 0, deref: bool = True) -> Optional[int]:
        """UE4 RIP-relative scan (x64).

        Finds pattern, applies *adjust* to the match VA, then reads the 32-bit
        RIP displacement at (match+3), computes the target VA as
        ``match_va + 7 + rip_offset``.

        deref=True  (GNames):   return  *u64(target)
        deref=False (GObjects): return  target
        """
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
                match_va = pos + idx + adjust
                # Read the 32-bit signed RIP displacement
                raw = self._backend.read(match_va + rel_off, 4)
                if not raw or len(raw) < 4:
                    return None
                rip_disp = struct.unpack_from("<i", raw)[0]
                target   = match_va + rel_off + 4 + rip_disp
                if deref:
                    return self._backend.rptr(target, is64=True)
                return target
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
# ProcessEvent VTable detection
# ─────────────────────────────────────────────────────────────────────────────

def find_process_event(
    backend: MemoryBackend,
    uobject_va: int,
    pe_pattern: bytes,
    pe_mask: str,
    pe_scan_limit: int = 0x200,
    is64: bool = False,
) -> Optional[int]:
    """Walk the vtable of *uobject_va* to locate ProcessEvent.

    For each vtable slot (up to *pe_scan_limit* entries) the function reads the
    slot's function pointer, reads the first ``len(pe_pattern) + 32`` bytes at
    that address, then tries to match *pe_pattern* / *pe_mask*.

    Returns the **0-based vtable index** of the matching slot, or ``None``.

    Args:
        backend:        An open MemoryBackend with the target process attached.
        uobject_va:     VA of any live UObject (e.g. the first entry from GObjects).
        pe_pattern:     Byte pattern that appears at the start of ProcessEvent.
        pe_mask:        'x'/'?' mask of the same length.
        pe_scan_limit:  Maximum vtable entries to inspect (not bytes).
        is64:           True for x64 processes (UE4); pointer size = 8.
    """
    if not uobject_va or not pe_pattern:
        return None

    ptr_sz = 8 if is64 else 4
    # vtable pointer is at offset 0 of every UObject
    vtable_ptr = backend.rptr(uobject_va, is64)
    if not vtable_ptr or vtable_ptr < 0x10000:
        return None

    plen = len(pe_pattern)
    for i in range(pe_scan_limit):
        fn_va = backend.rptr(vtable_ptr + i * ptr_sz, is64)
        if not fn_va or fn_va < 0x10000:
            continue
        data = backend.read(fn_va, plen + 32)
        if not data or len(data) < plen:
            continue
        if PatternScanner._match(data, pe_pattern, pe_mask) is not None:
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
        if self.name_encoding == "utf-16-le":
            # Find the 2-byte null terminator on an even boundary
            end = -1
            for i in range(0, len(raw) - 1, 2):
                if raw[i] == 0 and raw[i + 1] == 0:
                    end = i
                    break
            raw = raw[:end] if end >= 0 else raw
        else:
            end = raw.find(b"\x00")
            raw = raw[:end] if end >= 0 else raw
        return raw.decode(self.name_encoding, errors="replace")

    # ── public API ────────────────────────────────────────────────────────

    def dump_names(self, cb=None, item_cb=None) -> Dict[int, str]:
        """Dump GNames.

        cb(i, total)       -- called every 500 entries (progress bar).
        item_cb(idx, name) -- called for every valid name found (live feed).
        """
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
                if item_cb:
                    item_cb(i, name)
            if cb and i % 500 == 0:
                cb(i, count)
        return out

    def dump_objects(self, names: Dict[int, str], cb=None, item_cb=None) -> List[Dict]:
        """Dump GObjects.

        cb(i, total) -- called every 500 entries (progress bar).
        item_cb(obj) -- called for every object found (live feed).
        """
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
            obj = {
                "index":      i,
                "ptr":        ptr,
                "name_index": ni,
                "name":       names.get(ni, f"?{ni}"),
            }
            out.append(obj)
            if item_cb:
                item_cb(obj)
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


# ─────────────────────────────────────────────────────────────────────────────
# UE4 memory reader  (x64, RIP-relative patterns)
# ─────────────────────────────────────────────────────────────────────────────

class UE4Reader:
    """Back-end-agnostic UE4 GNames / GObjects reader.

    GNames layout — TStaticIndirectArrayThreadSafeRead<FNameEntry,2097152,16384>
        gnames_va + 0x000 : 128 × u64 chunk pointers
        gnames_va + 0x400 : int32 NumElements

        To read name at index i:
            chunk_idx  = i // ELEMENTS_PER_CHUNK
            within     = i  % ELEMENTS_PER_CHUNK
            chunk_ptr  = u64(gnames_va + chunk_idx * 8)
            entry_ptr  = u64(chunk_ptr  + within    * 8)
            name_str   = str(entry_ptr  + name_str_off)

    GObjects layouts:
        fuobj_chunked (Fortnite / PUBG / Paragon / UT4):
            FUObjectArray.ObjObjects (TUObjectArray) at gobjects_va
            TUObjectArray.Objects  (ptr)  at gobjects_va + 0x10
            TUObjectArray.NumElems (i32)  at gobjects_va + 0x1C
            item_i = Objects + i * 0x18,  object_ptr = *u64(item_i)

        fuobj_tarray (ARK / AITD):
            FUObjectArray.ObjObjects (TArray<UObject*>) at gobjects_va
            TArray.Data  (ptr)  at gobjects_va + 0x10
            TArray.Count (i32)  at gobjects_va + 0x18
            object_ptr = *u64(Data + i * 8)
    """

    ELEMENTS_PER_CHUNK = 16384
    CHUNK_TABLE_SIZE   = 128          # (2 097 152 + 16383) // 16384

    def __init__(self,
                 backend:        MemoryBackend,
                 gobjects_va:    int = 0,
                 gnames_va:      int = 0,
                 name_field_off: int = 0x18,
                 name_str_off:   int = 0x10,
                 name_encoding:  str = "ascii",
                 gobj_layout:    str = "fuobj_chunked") -> None:
        self.backend        = backend
        self.gobjects_va    = gobjects_va
        self.gnames_va      = gnames_va
        self.name_field_off = name_field_off
        self.name_str_off   = name_str_off
        self.name_encoding  = name_encoding
        self.gobj_layout    = gobj_layout

    # ── GNames ────────────────────────────────────────────────────────────

    def dump_names(self, cb=None, item_cb=None) -> Dict[int, str]:
        """Read GNames via the chunked TStaticIndirectArray."""
        # Determine element count
        num_elements = self.backend.ru32(self.gnames_va + self.CHUNK_TABLE_SIZE * 8)
        if not num_elements or num_elements > 5_000_000:
            return {}
        out: Dict[int, str] = {}
        for i in range(num_elements):
            chunk_idx = i // self.ELEMENTS_PER_CHUNK
            within    = i  % self.ELEMENTS_PER_CHUNK
            if chunk_idx >= self.CHUNK_TABLE_SIZE:
                break
            chunk_ptr = self.backend.rptr(self.gnames_va + chunk_idx * 8, is64=True)
            if not chunk_ptr:
                continue
            entry_ptr = self.backend.rptr(chunk_ptr + within * 8, is64=True)
            if not entry_ptr:
                continue
            raw = self.backend.read(entry_ptr + self.name_str_off, 512)
            if not raw:
                continue
            end = raw.find(b"\x00")
            raw = raw[:end] if end >= 0 else raw
            name = raw.decode(self.name_encoding, errors="replace")
            if name:
                out[i] = name
                if item_cb:
                    item_cb(i, name)
            if cb and i % 500 == 0:
                cb(i, num_elements)
        return out

    # ── GObjects ──────────────────────────────────────────────────────────

    def dump_objects(self, names: Dict[int, str], cb=None, item_cb=None) -> List[Dict]:
        if self.gobj_layout == "fuobj_chunked":
            return self._dump_objects_chunked(names, cb, item_cb)
        return self._dump_objects_tarray(names, cb, item_cb)

    def _dump_objects_chunked(self, names, cb, item_cb) -> List[Dict]:
        """FUObjectArray + TUObjectArray (Fortnite/PUBG/Paragon/UT4)."""
        objects_ptr = self.backend.rptr(self.gobjects_va + 0x10, is64=True)
        num_elems   = self.backend.ru32(self.gobjects_va + 0x1C)
        if not objects_ptr or not num_elems:
            return []
        ITEM_SZ = 0x18
        out: List[Dict] = []
        for i in range(num_elems):
            item_addr  = objects_ptr + i * ITEM_SZ
            obj_ptr    = self.backend.rptr(item_addr, is64=True)
            if not obj_ptr:
                continue
            ni = self.backend.ru32(obj_ptr + self.name_field_off)
            if ni is None:
                continue
            obj = {"index": i, "ptr": obj_ptr, "name_index": ni,
                   "name": names.get(ni, f"?{ni}")}
            out.append(obj)
            if item_cb:
                item_cb(obj)
            if cb and i % 500 == 0:
                cb(i, num_elems)
        return out

    def _dump_objects_tarray(self, names, cb, item_cb) -> List[Dict]:
        """FUObjectArray + TArray<UObject*> (ARK/AITD)."""
        data_ptr  = self.backend.rptr(self.gobjects_va + 0x10, is64=True)
        num_elems = self.backend.ru32(self.gobjects_va + 0x18)
        if not data_ptr or not num_elems:
            return []
        out: List[Dict] = []
        for i in range(num_elems):
            obj_ptr = self.backend.rptr(data_ptr + i * 8, is64=True)
            if not obj_ptr:
                continue
            ni = self.backend.ru32(obj_ptr + self.name_field_off)
            if ni is None:
                continue
            obj = {"index": i, "ptr": obj_ptr, "name_index": ni,
                   "name": names.get(ni, f"?{ni}")}
            out.append(obj)
            if item_cb:
                item_cb(obj)
            if cb and i % 500 == 0:
                cb(i, num_elems)
        return out

