"""offset_finder.py — Remote-memory UE struct offset discovery.

Python port of Dumper-7's OffsetFinder for out-of-process use via MemoryBackend.
Supports UE3 (32/64-bit), UE4 (64-bit), and UE5 (64-bit).

Key algorithms adapted from:
  Dumper-7/Dumper/Engine/Private/OffsetFinder/OffsetFinder.cpp
  Dumper-7/Dumper/Engine/Public/OffsetFinder/OffsetFinder.h
  Dumper-7/Dumper/Engine/Public/OffsetFinder/Offsets.h

All reads are performed through a MemoryBackend (out-of-process / DMA-safe).
"""
from __future__ import annotations

import struct
from typing import Callable, Dict, List, Optional, Tuple

try:
    from ..backends import MemoryBackend
    from .offsets import DiscoveredOffsets, NOT_FOUND
except ImportError:
    try:
        from backends import MemoryBackend              # type: ignore[no-redef]
        from utils.offsets import DiscoveredOffsets, NOT_FOUND  # type: ignore[no-redef]
    except ImportError:
        from backends import MemoryBackend              # type: ignore[no-redef]
        from offsets import DiscoveredOffsets, NOT_FOUND        # type: ignore[no-redef]


# ── Constants matching Dumper-7 ────────────────────────────────────────────────

# EObjectFlags: RF_Standalone | RF_Native | RF_Public — very common in early objects
_FLAGS_COMMON_VALUE   = 0x43
_FLAGS_MIN_MATCHES    = 0xA0      # 160  (Dumper-7: MinNumFlagValuesRequiredAtOffset)

# FChunkedFixedUObjectArray chunk layout
_GO_CHUNK_ELEMENTS    = 0x10000   # default 65 536 items per chunk
_GO_ITEM_SIZE_18      = 0x18      # FUObjectItem on UE4.21+ (ptr+flags+index+serial+pad)
_GO_ITEM_SIZE_10      = 0x10      # FUObjectItem on early UE4 (ptr+flags+index)

# TStaticIndirectArray (GNames UE4) layout
_GN_MAX_CHUNKS         = 128
_GN_ELEMENTS_PER_CHUNK = 16384

# FNamePool (UE5)
_GN5_CHUNK_SIZE        = 0x40000  # bytes per FNamePool chunk


class OffsetFinder:
    """Out-of-process UE struct offset discovery engine.

    Usage::

        finder = OffsetFinder(
            backend     = my_backend,
            gobjects_va = 0x12345678,
            gnames_va   = 0x87654321,
            is64        = True,
            ue_version  = "UE4",
            gobj_layout = "fuobj_chunked",
            gnam_layout = "tarray",
        )
        offsets = finder.find_all(progress_cb=lambda msg, pct: print(msg))
    """

    def __init__(self,
                 backend:     MemoryBackend,
                 gobjects_va: int,
                 gnames_va:   int,
                 is64:        bool = True,
                 ue_version:  str  = "UE4",
                 gobj_layout: str  = "fuobj_chunked",
                 gnam_layout: str  = "tarray") -> None:
        self._b        = backend
        self._gobj_va  = gobjects_va
        self._gnam_va  = gnames_va
        self._is64     = is64
        self._ue_ver   = ue_version
        self._gl_obj   = gobj_layout
        self._gl_nam   = gnam_layout
        self._ptr_sz   = 8 if is64 else 4
        self._min_off  = 0x08  # skip VTable

        # Lazy caches
        self._obj_ptrs:  Optional[List[int]]      = None
        self._names_map: Optional[Dict[int, str]] = None

    # ═══════════════════════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════════════════════

    def find_all(self,
                 progress_cb:  Optional[Callable] = None,
                 game_name:    str = "",
                 process_name: str = "") -> DiscoveredOffsets:
        """Run all offset finders and return a DiscoveredOffsets instance.

        ``progress_cb(message: str, fraction: float)`` is optional.
        """
        def _cb(msg: str, pct: float) -> None:
            if progress_cb:
                progress_cb(msg, pct)

        out = DiscoveredOffsets(
            is64         = self._is64,
            ue_version   = self._ue_ver,
            gobjects_va  = self._gobj_va,
            gnames_va    = self._gnam_va,
            gobj_layout  = self._gl_obj,
            gnam_layout  = self._gl_nam,
            game_name    = game_name,
            process_name = process_name,
        )

        # ── 1. Enumerate objects ──────────────────────────────────────────────
        _cb("OffsetFinder: enumerating GObjects…", 0.00)
        obj_ptrs = self._enum_objects(512)
        if len(obj_ptrs) < 10:
            _cb(f"OffsetFinder: only {len(obj_ptrs)} objects — "
                "applying defaults without discovery", 1.0)
            _apply_defaults(out)
            return out

        # ── 2. Enumerate names ────────────────────────────────────────────────
        _cb("OffsetFinder: enumerating GNames…", 0.05)
        names = self._enum_names(512)

        # ── 3. UObject fields ─────────────────────────────────────────────────
        _cb("OffsetFinder: FindUObjectFlagsOffset…", 0.10)
        out.uobj_flags = self._find_uobj_flags(obj_ptrs)

        _cb("OffsetFinder: FindUObjectIndexOffset…", 0.15)
        out.uobj_index = self._find_uobj_index()

        _cb("OffsetFinder: FindUObjectClassOffset…", 0.22)
        out.uobj_class = self._find_uobj_class(obj_ptrs, out.uobj_flags)

        _cb("OffsetFinder: FindUObjectNameOffset…", 0.30)
        out.uobj_name = self._find_uobj_name(obj_ptrs, names, out.uobj_class)

        _cb("OffsetFinder: FindUObjectOuterOffset…", 0.37)
        out.uobj_outer = self._find_uobj_outer(obj_ptrs, out.uobj_class, out.uobj_name)

        # ── 4. FName settings ─────────────────────────────────────────────────
        fname_sz, str_off, encoding = self._init_fname_settings()
        out.fname_sz             = fname_sz
        out.fname_entry_str_off  = str_off
        out.fname_entry_encoding = encoding
        if self._gl_nam == "namepool":
            out.fname_entry_str_off    = 0x02
            out.fname_entry_header_off = 0x00

        # ── 5. UStruct / UField ───────────────────────────────────────────────
        _cb("OffsetFinder: FindUFieldNextOffset…", 0.42)
        out.ufield_next = self._find_ufield_next(obj_ptrs, out)

        _cb("OffsetFinder: FindSuperOffset…", 0.47)
        out.ustruct_super = self._find_ustruct_super(obj_ptrs, out)

        _cb("OffsetFinder: FindChildOffset…", 0.51)
        out.ustruct_children = self._find_ustruct_children(obj_ptrs, out)

        _cb("OffsetFinder: FindStructSizeOffset…", 0.55)
        out.ustruct_size = self._find_ustruct_size(obj_ptrs, out)

        # ── 6. FField offsets (UE4.25+) ───────────────────────────────────────
        if self._ue_ver in ("UE4", "UE5"):
            _cb("OffsetFinder: FField offsets…", 0.58)
            out.ffield_class = 0x00
            out.ffield_owner = 0x08
            out.ffield_next  = self._find_ffield_next(obj_ptrs, out)
            out.ffield_name  = self._find_ffield_name(obj_ptrs, names, out)
            if out.ffield_name != NOT_FOUND:
                out.ffield_flags = out.ffield_name + fname_sz
            out.ustruct_childprops = self._find_ustruct_childprops(obj_ptrs, out)

        # ── 7. Property offsets ───────────────────────────────────────────────
        _cb("OffsetFinder: Property base offsets…", 0.64)
        p_base = self._calc_prop_base()
        out.prop_arraydim = p_base
        if p_base != NOT_FOUND:
            out.prop_elemsize  = p_base + 0x04
            out.prop_flags     = p_base + 0x08
            out.prop_offset    = p_base + 0x1C
            out.prop_base_sz   = p_base + 0x40
            sub = out.prop_base_sz
            out.byteprop_enum   = sub
            out.boolprop_base   = sub
            out.objprop_class   = sub
            out.clsprop_meta    = sub + self._ptr_sz
            out.strprop_struct  = sub
            out.arrprop_inner   = sub
            out.mapprop_base    = sub
            out.setprop_elem    = sub
            out.enumprop_base   = sub
            out.delprop_func    = sub
            out.intprop_class   = sub

        # ── 8. UFunction.Flags ────────────────────────────────────────────────
        _cb("OffsetFinder: FindFunctionFlagsOffset…", 0.72)
        out.ufunc_flags = self._find_ufunc_flags(obj_ptrs, out)

        # ── 9. UEnum.Names ────────────────────────────────────────────────────
        _cb("OffsetFinder: FindEnumNamesOffset…", 0.78)
        out.uenum_names = self._find_uenum_names(obj_ptrs, out)

        # ── 10. Apply fallback defaults for any unresolved offsets ─────────────
        _cb("OffsetFinder: applying fallback defaults…", 0.92)
        _apply_defaults(out)

        # ── 11. Compute confidence ─────────────────────────────────────────────
        key_fields = [
            out.uobj_flags, out.uobj_index, out.uobj_class,
            out.uobj_name, out.uobj_outer, out.ufield_next,
            out.ustruct_super, out.ustruct_children, out.ustruct_size,
        ]
        found = sum(1 for f in key_fields if f != NOT_FOUND)
        out.confidence = int(found / len(key_fields) * 100)

        _cb(f"OffsetFinder: complete — confidence {out.confidence}%", 1.0)
        return out

    # ═══════════════════════════════════════════════════════════════════════════
    # GObjects enumeration
    # ═══════════════════════════════════════════════════════════════════════════

    def _enum_objects(self, max_count: int = 512) -> List[int]:
        if self._obj_ptrs is not None:
            return self._obj_ptrs[:max_count]

        if self._gl_obj == "fuobj_chunked":
            ptrs = self._enum_objects_chunked(max_count)
        elif self._gl_obj == "fuobj_tarray":
            ptrs = self._enum_objects_fuobj_tarray(max_count)
        else:
            ptrs = self._enum_objects_tarray(max_count)

        self._obj_ptrs = ptrs
        return ptrs[:max_count]

    def _enum_objects_tarray(self, max_count: int) -> List[int]:
        ps = self._ptr_sz
        data = self._b.rptr(self._gobj_va, self._is64) or 0
        cnt  = self._b.ru32(self._gobj_va + ps) or 0
        ptrs: List[int] = []
        for i in range(min(cnt, max_count * 4)):
            obj = self._b.rptr(data + i * ps, self._is64)
            if obj:
                ptrs.append(obj)
                if len(ptrs) >= max_count:
                    break
        return ptrs

    def _enum_objects_fuobj_tarray(self, max_count: int) -> List[int]:
        ps   = self._ptr_sz
        data = self._b.rptr(self._gobj_va, self._is64) or 0
        cnt  = self._b.ru32(self._gobj_va + ps * 2) or 0
        item = 0x18 if self._is64 else 0x10
        ptrs: List[int] = []
        for i in range(min(cnt, max_count * 4)):
            obj = self._b.rptr(data + i * item, self._is64)
            if obj:
                ptrs.append(obj)
                if len(ptrs) >= max_count:
                    break
        return ptrs

    def _enum_objects_chunked(self, max_count: int) -> List[int]:
        """FChunkedFixedUObjectArray — tries both FUObjectItem sizes (0x10 / 0x18)."""
        ps          = self._ptr_sz
        chunks_base = self._b.rptr(self._gobj_va, self._is64) or 0
        if not chunks_base:
            return []

        num_elements = self._b.ru32(self._gobj_va + 0x14) or 0
        if not (64 <= num_elements <= 10_000_000):
            num_elements = self._b.ru32(self._gobj_va + 0x10) or 0
        if not (64 <= num_elements <= 10_000_000):
            return []

        for item_sz in (_GO_ITEM_SIZE_18, _GO_ITEM_SIZE_10):
            ptrs: List[int] = []
            for i in range(min(num_elements, max_count * 4)):
                ci    = i // _GO_CHUNK_ELEMENTS
                wi    = i  % _GO_CHUNK_ELEMENTS
                chunk = self._b.rptr(chunks_base + ci * ps, self._is64)
                if not chunk:
                    break
                obj = self._b.rptr(chunk + wi * item_sz, self._is64)
                if obj:
                    ptrs.append(obj)
                if len(ptrs) >= max_count:
                    break
            if len(ptrs) >= 10:
                return ptrs
        return []

    def _obj_at_index(self, idx: int) -> int:
        """Read UObject* at GObjects[idx]."""
        ps = self._ptr_sz
        if self._gl_obj == "fuobj_chunked":
            chunks_base = self._b.rptr(self._gobj_va, self._is64) or 0
            for item_sz in (_GO_ITEM_SIZE_18, _GO_ITEM_SIZE_10):
                ci    = idx // _GO_CHUNK_ELEMENTS
                wi    = idx  % _GO_CHUNK_ELEMENTS
                chunk = self._b.rptr(chunks_base + ci * ps, self._is64)
                if not chunk:
                    continue
                obj = self._b.rptr(chunk + wi * item_sz, self._is64)
                if obj:
                    return obj
            return 0
        else:
            data = self._b.rptr(self._gobj_va, self._is64) or 0
            return self._b.rptr(data + idx * ps, self._is64) or 0

    # ═══════════════════════════════════════════════════════════════════════════
    # GNames enumeration
    # ═══════════════════════════════════════════════════════════════════════════

    def _enum_names(self, max_count: int = 512) -> Dict[int, str]:
        if self._names_map is not None:
            return dict(list(self._names_map.items())[:max_count])

        if self._gl_nam == "namepool":
            names = self._enum_names_namepool(max_count)
        elif self._gl_nam == "chunked":
            names = self._enum_names_chunked_ue4(max_count)
        else:
            names = self._enum_names_tarray(max_count)

        self._names_map = names
        return dict(list(names.items())[:max_count])

    def _enum_names_tarray(self, max_count: int) -> Dict[int, str]:
        ps   = self._ptr_sz
        data = self._b.rptr(self._gnam_va, self._is64) or 0
        cnt  = self._b.ru32(self._gnam_va + ps) or 0
        names: Dict[int, str] = {}
        for i in range(min(cnt, max_count)):
            entry = self._b.rptr(data + i * ps, self._is64)
            if not entry:
                continue
            for str_off in (0x10, 0x0C, 0x14, 0x08):
                raw = self._b.read(entry + str_off, 64)
                if not raw:
                    continue
                end = raw.find(b"\x00")
                if end < 2:
                    continue
                chunk = raw[:end]
                if all(32 <= b < 128 for b in chunk):
                    names[i] = chunk.decode("ascii", errors="replace")
                    break
        return names

    def _enum_names_chunked_ue4(self, max_count: int) -> Dict[int, str]:
        chunk_table_sz = _GN_MAX_CHUNKS
        epc            = _GN_ELEMENTS_PER_CHUNK
        num_elements   = self._b.ru32(self._gnam_va + chunk_table_sz * 8) or 0
        if not (64 <= num_elements <= 5_000_000):
            return {}
        names: Dict[int, str] = {}
        for i in range(min(num_elements, max_count)):
            ci    = i // epc
            wi    = i  % epc
            chunk = self._b.rptr(self._gnam_va + ci * 8, is64=True)
            if not chunk:
                continue
            entry = self._b.rptr(chunk + wi * 8, is64=True)
            if not entry:
                continue
            raw = self._b.read(entry + 0x10, 64)
            if not raw:
                continue
            end = raw.find(b"\x00")
            if end < 1:
                continue
            chunk_bytes = raw[:end]
            if all(32 <= b < 128 for b in chunk_bytes):
                names[i] = chunk_bytes.decode("ascii", errors="replace")
        return names

    def _enum_names_namepool(self, max_count: int) -> Dict[int, str]:
        """UE5 FNamePool: chunk-based, uint16 header per entry."""
        chunks_base = self._gnam_va + 0x10
        names: Dict[int, str] = {}

        # Read chunk 0 to detect the length shift (4, 5, or 6)
        chunk0_ptr = self._b.rptr(chunks_base, is64=True)
        if not chunk0_ptr:
            return names
        chunk0_data = self._b.read(chunk0_ptr, _GN5_CHUNK_SIZE // 4) or b""

        target = b"ByteProperty"
        length_shift = 4
        for shift in (4, 5, 6):
            found_shift = False
            for off in range(0, min(len(chunk0_data) - len(target) - 2, 0x8000), 2):
                try:
                    hdr = struct.unpack_from("<H", chunk0_data, off)[0]
                except struct.error:
                    break
                is_wide    = hdr & 1
                entry_len  = hdr >> shift
                if is_wide or entry_len != len(target):
                    continue
                if chunk0_data[off + 2: off + 2 + entry_len] == target:
                    length_shift = shift
                    found_shift  = True
                    break
            if found_shift:
                break

        # Walk chunk 0 collecting names
        off = 0
        idx = 0
        while off < len(chunk0_data) - 2 and idx < max_count:
            try:
                hdr = struct.unpack_from("<H", chunk0_data, off)[0]
            except struct.error:
                break
            is_wide   = hdr & 1
            entry_len = hdr >> length_shift
            if entry_len < 1 or entry_len > 256:
                off += 2
                continue
            byte_len = entry_len * (2 if is_wide else 1)
            raw = chunk0_data[off + 2: off + 2 + byte_len]
            if len(raw) < byte_len:
                break
            try:
                name = (raw.decode("utf-16-le", errors="replace")
                        if is_wide else raw.decode("ascii", errors="replace"))
                name = name.rstrip("\x00")
            except Exception:
                name = ""
            if name and len(name) >= 2 and all(32 <= ord(c) < 128 for c in name if not is_wide):
                names[idx] = name
                idx += 1
            stride = 2 + byte_len
            off += stride + (stride % 2)  # align to 2 bytes
        return names

    # ═══════════════════════════════════════════════════════════════════════════
    # Low-level helpers
    # ═══════════════════════════════════════════════════════════════════════════

    def _rptr_at(self, ptr: int, off: int) -> int:
        v = self._b.rptr(ptr + off, self._is64)
        return v or 0

    def _ru32_at(self, ptr: int, off: int) -> int:
        v = self._b.ru32(ptr + off)
        return v if v is not None else 0

    def _ri32_at(self, ptr: int, off: int) -> int:
        raw = self._b.read(ptr + off, 4)
        if not raw or len(raw) < 4:
            return 0
        return struct.unpack_from("<i", raw)[0]

    def _is_valid_ptr(self, ptr: int) -> bool:
        if not ptr:
            return False
        if self._is64:
            return 0x10000 < ptr < 0x0000_7FFF_FFFF_FFFF
        return 0x10000 < ptr < 0xFFFF_0000

    def _read_obj(self, ptr: int, size: int = 0x100) -> Optional[bytes]:
        if not ptr:
            return None
        return self._b.read(ptr, size)

    # ═══════════════════════════════════════════════════════════════════════════
    # FindUObjectFlagsOffset  (Dumper-7: FindUObjectFlagsOffset)
    # ═══════════════════════════════════════════════════════════════════════════

    def _find_uobj_flags(self, obj_ptrs: List[int]) -> int:
        """Scan objects for common EObjectFlags value 0x43 at each aligned offset.

        Adapted from Dumper-7::FindUObjectFlagsOffset().
        """
        MAX_OFF = 0x20
        counts: Dict[int, int] = {}
        for ptr in obj_ptrs[:512]:
            raw = self._b.read(ptr, MAX_OFF + 4)
            if not raw or len(raw) < MAX_OFF:
                continue
            for off in range(self._min_off, MAX_OFF, 4):
                if off + 4 > len(raw):
                    break
                val = struct.unpack_from("<I", raw, off)[0]
                if val == _FLAGS_COMMON_VALUE:
                    counts[off] = counts.get(off, 0) + 1

        for off in sorted(counts, key=counts.__getitem__, reverse=True):
            if counts[off] >= _FLAGS_MIN_MATCHES:
                return off
        # Fallback: best count if >= 20
        if counts:
            best = max(counts, key=counts.__getitem__)
            if counts[best] >= 20:
                return best
        return NOT_FOUND

    # ═══════════════════════════════════════════════════════════════════════════
    # FindUObjectIndexOffset  (Dumper-7: FindUObjectIndexOffset)
    # ═══════════════════════════════════════════════════════════════════════════

    def _find_uobj_index(self) -> int:
        """Find InternalIndex by reading objects at known GObjects positions.

        We read GObjects[0x055] and GObjects[0x123] and look for their index
        values in the object bytes.  Adapted from Dumper-7::FindUObjectIndexOffset().
        """
        pairs: List[Tuple[int, int]] = []
        for expected in (0x055, 0x123, 0x3FF):
            ptr = self._obj_at_index(expected)
            if ptr:
                pairs.append((ptr, expected))

        if not pairs:
            # Fallback: assume first non-null objects have index = their position
            ptrs = self._enum_objects(20)
            for i, ptr in enumerate(ptrs[1:10], start=1):
                pairs.append((ptr, i))
            if not pairs:
                return NOT_FOUND

        best_off   = NOT_FOUND
        best_count = 0
        for off in range(self._ptr_sz, 0x1A0, 4):
            matches = 0
            for ptr, expected in pairs:
                raw = self._b.read(ptr + off, 4)
                if raw and len(raw) == 4:
                    if struct.unpack_from("<i", raw)[0] == expected:
                        matches += 1
            if matches > best_count:
                best_count = matches
                best_off   = off

        return best_off if best_count >= max(1, len(pairs) - 1) else NOT_FOUND

    # ═══════════════════════════════════════════════════════════════════════════
    # FindUObjectClassOffset  (Dumper-7: FindUObjectClassOffset)
    # ═══════════════════════════════════════════════════════════════════════════

    def _find_uobj_class(self, obj_ptrs: List[int], flags_off: int) -> int:
        """Find UClass* field by looking for a cyclic class pointer.

        UClass 'CoreUObject.Class' has its own Class field pointing to itself.
        Adapted from Dumper-7::FindUObjectClassOffset().
        """
        ps       = self._ptr_sz
        obj_set  = set(obj_ptrs[:256])
        min_off  = max(self._min_off,
                       (flags_off + 4) if flags_off != NOT_FOUND else self._min_off)

        best_off   = NOT_FOUND
        best_score = 0

        for off in range(min_off, 0x1A0, ps):
            cyclic   = 0
            self_ref = 0
            valid    = 0
            for ptr in obj_ptrs[:64]:
                raw = self._b.read(ptr + off, ps)
                if not raw or len(raw) < ps:
                    continue
                cls_ptr = (struct.unpack_from("<Q", raw)[0] if self._is64
                           else struct.unpack_from("<I", raw)[0])
                if not self._is_valid_ptr(cls_ptr):
                    continue
                valid += 1
                if cls_ptr in obj_set:
                    self_ref += 1
                    inner = self._b.rptr(cls_ptr + off, self._is64)
                    if inner == cls_ptr:
                        cyclic += 1
            score = cyclic * 3 + self_ref
            if score > best_score and valid >= 5:
                best_score = score
                best_off   = off

        return best_off if best_score > 0 else NOT_FOUND

    # ═══════════════════════════════════════════════════════════════════════════
    # FindUObjectNameOffset  (Dumper-7: FindUObjectNameOffset)
    # ═══════════════════════════════════════════════════════════════════════════

    def _find_uobj_name(self, obj_ptrs: List[int],
                         names: Dict[int, str],
                         class_off: int) -> int:
        """Find FName.CompIdx offset by checking for valid name indices.

        Adapted from Dumper-7::FindUObjectNameOffset().
        """
        if not names:
            return NOT_FOUND

        max_ni   = max(names.keys()) + 1
        forbidden = {class_off} if class_off != NOT_FOUND else set()

        scores: Dict[int, int] = {}
        for off in range(self._min_off, 0x1A0, 4):
            if off in forbidden:
                continue
            valid = sum(
                1 for ptr in obj_ptrs[:64]
                if (lambda r: r is not None and struct.unpack_from("<I", r)[0] < max_ni)(
                    self._b.read(ptr + off, 4))
            )
            if valid >= 5:
                scores[off] = valid

        if not scores:
            return NOT_FOUND

        # Among top candidates, prefer one that gives decodable names
        for off in sorted(scores, key=scores.__getitem__, reverse=True):
            hits = 0
            for ptr in obj_ptrs[:20]:
                raw = self._b.read(ptr + off, 4)
                if not raw:
                    continue
                idx = struct.unpack_from("<I", raw)[0]
                if idx in names:
                    hits += 1
            if hits >= 3:
                return off

        return max(scores, key=scores.__getitem__)

    # ═══════════════════════════════════════════════════════════════════════════
    # FindUObjectOuterOffset  (Dumper-7: FindUObjectOuterOffset)
    # ═══════════════════════════════════════════════════════════════════════════

    def _find_uobj_outer(self, obj_ptrs: List[int],
                          class_off: int, name_off: int) -> int:
        """Find UObject* Outer by looking for a mixed null/valid pointer field.

        Adapted from Dumper-7::FindUObjectOuterOffset().
        """
        ps        = self._ptr_sz
        forbidden = {0, class_off} if class_off != NOT_FOUND else {0}
        start     = ((name_off + 8) if name_off != NOT_FOUND
                     else (self._min_off + ps))
        start     = (start + ps - 1) & ~(ps - 1)

        best_off   = NOT_FOUND
        best_count = 0
        for off in range(start, start + 0x60, ps):
            if off in forbidden:
                continue
            null_cnt  = 0
            valid_cnt = 0
            for ptr in obj_ptrs[:64]:
                raw = self._b.read(ptr + off, ps)
                if not raw or len(raw) < ps:
                    continue
                outer = (struct.unpack_from("<Q", raw)[0] if self._is64
                         else struct.unpack_from("<I", raw)[0])
                if outer == 0:
                    null_cnt += 1
                elif self._is_valid_ptr(outer):
                    valid_cnt += 1
            total = null_cnt + valid_cnt
            if total > best_count and null_cnt > 0 and valid_cnt > 0:
                best_count = total
                best_off   = off

        # Fallback: first plausible ptr-or-null field after Name
        if best_off == NOT_FOUND:
            for off in range(start, start + 0x80, ps):
                if off in forbidden:
                    continue
                cnt = sum(
                    1 for ptr in obj_ptrs[:32]
                    if (lambda v: v == 0 or self._is_valid_ptr(v))(
                        self._rptr_at(ptr, off))
                )
                if cnt >= 10:
                    best_off = off
                    break

        return best_off

    # ═══════════════════════════════════════════════════════════════════════════
    # InitFNameSettings  (Dumper-7: InitFNameSettings)
    # ═══════════════════════════════════════════════════════════════════════════

    def _init_fname_settings(self) -> Tuple[int, int, str]:
        """Return (fname_sz, fname_entry_str_off, encoding)."""
        if self._ue_ver in ("UE4", "UE5"):
            return 8, 0x10, "ascii"
        if self._ue_ver == "UE3":
            return 8, 0x10, "ascii"
        if self._ue_ver == "UE2":
            return 8, 0x10, "utf-16-le"
        # UE1
        return 4, 0x0C, "utf-16-le"

    # ═══════════════════════════════════════════════════════════════════════════
    # FindUFieldNextOffset  (Dumper-7: FindUFieldNextOffset)
    # ═══════════════════════════════════════════════════════════════════════════

    def _find_ufield_next(self, obj_ptrs: List[int],
                           offsets: DiscoveredOffsets) -> int:
        """Find UField::Next by looking for valid pointer chains in Field objects.

        Adapted from Dumper-7::FindUFieldNextOffset().
        """
        struct_ptrs = self._objects_of_kind(obj_ptrs, offsets, "Function", 2)
        if len(struct_ptrs) < 2:
            struct_ptrs = self._objects_of_kind(obj_ptrs, offsets, "Struct", 2)
        if len(struct_ptrs) < 2:
            return NOT_FOUND

        defined = [v for v in [offsets.uobj_flags, offsets.uobj_index,
                                offsets.uobj_class, offsets.uobj_name,
                                offsets.uobj_outer] if v != NOT_FOUND]
        ps        = self._ptr_sz
        start_off = (max(defined) + 4 + ps - 1) & ~(ps - 1) if defined else self._min_off + ps
        return self._valid_ptr_at(struct_ptrs[0], struct_ptrs[1], start_off, start_off + 0x60)

    # ═══════════════════════════════════════════════════════════════════════════
    # FindFFieldNextOffset / FindFFieldNameOffset  (Dumper-7 equivalents)
    # ═══════════════════════════════════════════════════════════════════════════

    def _find_ffield_next(self, obj_ptrs: List[int],
                           offsets: DiscoveredOffsets) -> int:
        """Find FField::Next offset using Guid + Vector struct child-property chains."""
        ff_a = self._get_child_props_of(obj_ptrs, offsets, "Guid")
        ff_b = self._get_child_props_of(obj_ptrs, offsets, "Vector")
        if not ff_a or not ff_b:
            return 0x18  # UE4 standard
        return self._valid_ptr_at(ff_a, ff_b, 0x08, 0x48)

    def _find_ffield_name(self, obj_ptrs: List[int],
                           names: Dict[int, str],
                           offsets: DiscoveredOffsets) -> int:
        """Find FField::NamePrivate (FName) offset.

        Adapted from Dumper-7::FindFFieldNameOffset() / NewFindFFieldNameOffset().
        """
        ff_a = self._get_child_props_of(obj_ptrs, offsets, "Guid")
        if not ff_a:
            return 0x20  # UE4 standard
        max_ni = max(names.keys()) + 1 if names else 65536
        for off in range(0x18, 0x50, 4):
            raw = self._b.read(ff_a + off, 4)
            if not raw:
                continue
            idx = struct.unpack_from("<I", raw)[0]
            if 0 < idx < max_ni:
                return off
        return 0x20

    def _get_child_props_of(self, obj_ptrs: List[int],
                             offsets: DiscoveredOffsets,
                             struct_name: str) -> int:
        """Return ChildProperties FField* for a named UStruct."""
        if offsets.uobj_name == NOT_FOUND:
            return 0
        names    = self._names_map or {}
        max_ni   = max(names.keys()) + 1 if names else 0
        cp_off   = (offsets.ustruct_childprops
                    if offsets.ustruct_childprops != NOT_FOUND
                    else offsets.ustruct_children)
        if cp_off == NOT_FOUND:
            return 0
        for ptr in obj_ptrs[:256]:
            raw = self._b.read(ptr + offsets.uobj_name, 4)
            if not raw:
                continue
            ni = struct.unpack_from("<I", raw)[0]
            if ni >= max_ni or names.get(ni, "") != struct_name:
                continue
            return self._rptr_at(ptr, cp_off)
        return 0

    # ═══════════════════════════════════════════════════════════════════════════
    # UStruct layout finders
    # ═══════════════════════════════════════════════════════════════════════════

    def _find_ustruct_super(self, obj_ptrs: List[int],
                             offsets: DiscoveredOffsets) -> int:
        struct_ptrs = self._objects_of_kind(obj_ptrs, offsets, "Class", 4)
        if len(struct_ptrs) < 2:
            return NOT_FOUND
        ps        = self._ptr_sz
        next_off  = offsets.ufield_next
        start_off = ((next_off + ps) if next_off != NOT_FOUND
                     else self._min_off + ps * 2)
        start_off = (start_off + ps - 1) & ~(ps - 1)
        obj_set   = set(obj_ptrs[:256])
        for off in range(start_off, start_off + 0x60, ps):
            valid = sum(
                1 for ptr in struct_ptrs
                if (lambda v: v == 0 or (self._is_valid_ptr(v) and v in obj_set))(
                    self._rptr_at(ptr, off))
            )
            if valid >= len(struct_ptrs) - 1:
                return off
        return NOT_FOUND

    def _find_ustruct_children(self, obj_ptrs: List[int],
                                offsets: DiscoveredOffsets) -> int:
        struct_ptrs = self._objects_of_kind(obj_ptrs, offsets, "Class", 4)
        if len(struct_ptrs) < 2:
            return NOT_FOUND
        ps        = self._ptr_sz
        sup_off   = offsets.ustruct_super
        start_off = ((sup_off + ps) if sup_off != NOT_FOUND
                     else self._min_off + ps * 3)
        start_off = (start_off + ps - 1) & ~(ps - 1)
        return self._valid_ptr_at(struct_ptrs[0], struct_ptrs[1],
                                  start_off, start_off + 0x50)

    def _find_ustruct_childprops(self, obj_ptrs: List[int],
                                  offsets: DiscoveredOffsets) -> int:
        struct_ptrs = self._objects_of_kind(obj_ptrs, offsets, "Class", 4)
        if len(struct_ptrs) < 2:
            return NOT_FOUND
        ps        = self._ptr_sz
        ch_off    = offsets.ustruct_children
        start_off = ((ch_off + ps) if ch_off != NOT_FOUND
                     else self._min_off + ps * 4)
        start_off = (start_off + ps - 1) & ~(ps - 1)
        return self._valid_ptr_at(struct_ptrs[0], struct_ptrs[1],
                                  start_off, start_off + 0x50)

    def _find_ustruct_size(self, obj_ptrs: List[int],
                            offsets: DiscoveredOffsets) -> int:
        """Find PropertiesSize int32 field after Children/ChildProperties."""
        cp = offsets.ustruct_childprops
        ch = offsets.ustruct_children
        base = max((v for v in [cp, ch] if v != NOT_FOUND), default=0)
        start_off = base + self._ptr_sz if base else self._min_off + self._ptr_sz * 5
        struct_ptrs = self._objects_of_kind(obj_ptrs, offsets, "Class", 8)
        if not struct_ptrs:
            return NOT_FOUND
        for off in range(start_off, start_off + 0x20, 4):
            hits = 0
            for ptr in struct_ptrs:
                raw = self._b.read(ptr + off, 4)
                if not raw:
                    continue
                v = struct.unpack_from("<i", raw)[0]
                if 4 <= v <= 65536 and (v % 4) == 0:
                    hits += 1
            if hits >= max(3, len(struct_ptrs) // 2):
                return off
        return NOT_FOUND

    # ═══════════════════════════════════════════════════════════════════════════
    # Property base offset calculation
    # ═══════════════════════════════════════════════════════════════════════════

    def _calc_prop_base(self) -> int:
        """Calculate where property-specific fields start (ArrayDim).

        For FField (UE4.25+):  FFieldClass*(8) + FFieldVariant(16) + FField*Next(8)
                                + FName(8) + Flags(4) + pad(4) = 0x30
        For UProperty (UE3 32-bit): varies, hardcode 0x44.
        """
        if self._ue_ver in ("UE4", "UE5"):
            return 0x30
        if self._ue_ver == "UE3":
            return 0x44 if not self._is64 else 0x40
        return NOT_FOUND

    # ═══════════════════════════════════════════════════════════════════════════
    # FindFunctionFlagsOffset  (Dumper-7: FindFunctionFlagsOffset)
    # ═══════════════════════════════════════════════════════════════════════════

    def _find_ufunc_flags(self, obj_ptrs: List[int],
                           offsets: DiscoveredOffsets) -> int:
        func_ptrs = self._objects_of_kind(obj_ptrs, offsets, "Function", 6)
        if not func_ptrs:
            return NOT_FOUND
        start_off = offsets.ustruct_size if offsets.ustruct_size != NOT_FOUND else 0x40
        best_off   = NOT_FOUND
        best_count = 0
        for off in range(start_off, start_off + 0x60, 4):
            valid = 0
            for ptr in func_ptrs:
                raw = self._b.read(ptr + off, 4)
                if not raw:
                    continue
                v = struct.unpack_from("<I", raw)[0]
                if 0 < v < 0x200000:
                    valid += 1
            if valid > best_count:
                best_count = valid
                best_off   = off
        return best_off if best_count >= 2 else NOT_FOUND

    # ═══════════════════════════════════════════════════════════════════════════
    # FindEnumNamesOffset  (Dumper-7: FindEnumNamesOffset)
    # ═══════════════════════════════════════════════════════════════════════════

    def _find_uenum_names(self, obj_ptrs: List[int],
                           offsets: DiscoveredOffsets) -> int:
        enum_ptrs = self._objects_of_kind(obj_ptrs, offsets, "Enum", 4)
        if not enum_ptrs:
            return NOT_FOUND
        ps        = self._ptr_sz
        start_off = offsets.ustruct_size if offsets.ustruct_size != NOT_FOUND else 0x40
        for off in range(start_off, start_off + 0x60, ps):
            valid = 0
            for ptr in enum_ptrs:
                data  = self._rptr_at(ptr, off)
                count = self._ru32_at(ptr, off + ps) if data else 0
                if self._is_valid_ptr(data) and 2 <= count <= 512:
                    valid += 1
            if valid >= max(2, len(enum_ptrs) // 2):
                return off
        return NOT_FOUND

    # ═══════════════════════════════════════════════════════════════════════════
    # Shared helpers
    # ═══════════════════════════════════════════════════════════════════════════

    def _objects_of_kind(self, obj_ptrs: List[int],
                          offsets: DiscoveredOffsets,
                          class_suffix: str,
                          max_count: int = 4) -> List[int]:
        """Return object ptrs whose class name contains `class_suffix`."""
        if offsets.uobj_class == NOT_FOUND or offsets.uobj_name == NOT_FOUND:
            return []
        names  = self._names_map or {}
        max_ni = max(names.keys()) + 1 if names else 0
        result: List[int] = []
        for ptr in obj_ptrs[:256]:
            cls = self._rptr_at(ptr, offsets.uobj_class)
            if not cls:
                continue
            raw = self._b.read(cls + offsets.uobj_name, 4)
            if not raw:
                continue
            ni = struct.unpack_from("<I", raw)[0]
            if ni >= max_ni:
                continue
            if class_suffix.lower() in names.get(ni, "").lower():
                result.append(ptr)
                if len(result) >= max_count:
                    break
        return result

    def _valid_ptr_at(self, ptr_a: int, ptr_b: int,
                       start: int, end: int) -> int:
        """Return first offset where both ptr_a and ptr_b hold a valid VTable ptr.

        Adapted from Dumper-7::GetValidPointerOffset().
        """
        ps = self._ptr_sz
        for off in range(start, end, ps):
            va = self._rptr_at(ptr_a, off)
            vb = self._rptr_at(ptr_b, off)
            if self._is_valid_ptr(va) and self._is_valid_ptr(vb):
                # Check that the pointed objects also have readable VTables
                vt_a = self._b.rptr(va, self._is64) if va else None
                vt_b = self._b.rptr(vb, self._is64) if vb else None
                if self._is_valid_ptr(vt_a or 0) and self._is_valid_ptr(vt_b or 0):
                    return off
        return NOT_FOUND


# ─────────────────────────────────────────────────────────────────────────────
# Module-level helper
# ─────────────────────────────────────────────────────────────────────────────

def _apply_defaults(out: DiscoveredOffsets) -> None:
    """Apply UE-version-specific defaults for any NOT_FOUND fields."""
    if out.ue_version == "UE5":
        out.apply_ue5_defaults()
    elif out.ue_version == "UE4":
        out.apply_ue4_defaults()
    else:
        out.apply_ue3_defaults()
