"""sdk_gen.py — Full C++ SDK file generator for UESDKGen.

Produces one .hpp + one .cpp per UE package, plus a master SDK.hpp —
matching the output style of UnrealEngineSDKGenerator (KN4CK3R) but
driven by DMA / native memory access instead of in-process injection.

Supported engines : UE1 (partial), UE2, UE3  (all 32-bit TArray GObjects)
UE4               : basic header scaffold only (chunked GObjects/GNames
                    struct walking is not yet implemented)

Entry point:
  generate_sdk_files(
      backend, layout_name, names, objects,
      game_name, game_short, out_dir, progress_cb)

  layout_name  : "UE1" | "UE2" | "UE3" | "UE4"
  names        : {idx: str}   from reader.dump_names()
  objects      : [{ptr, name, index, ...}]  from reader.dump_objects()
  progress_cb  : callable(msg: str)  called with status updates
"""
from __future__ import annotations

import os
import re
import struct as _struct
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

try:
    from .backends import MemoryBackend
except ImportError:
    from backends import MemoryBackend  # type: ignore[no-redef]

# ─────────────────────────────────────────────────────────────────────────────
# Struct-layout constants per UE generation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Layout:
    # UObject
    uobj_outer:    int   # UObject* Outer
    uobj_name:     int   # FName.Index (int32) — name_field_off
    uobj_class:    int   # UClass*
    # UField
    ufld_next:     int   # UField* Next  (sibling)
    ufld_super:    int   # UField* SuperField  (set in UField for UE2,
                         #   or in UStruct for UE3 — same offset matters)
    # UStruct  (used for UScriptStruct, UClass, UState, UFunction)
    ustr_children:  int  # UField* Children
    ustr_propsize:  int  # uint32 PropertySize
    # UEnum (TArray<FName> at this absolute offset)
    uenum_names:    int
    fname_sz:       int  # bytes per FName entry: 4 (UE1/UE2) or 8 (UE3)
    # UFunction
    ufunc_flags:    int  # uint32 FunctionFlags
    ufunc_numparms: int  # uint8
    ufunc_parmsize: int  # uint16
    ufunc_retoff:   int  # uint16
    # UProperty (absolute offsets from object base)
    uprop_arraydim:  int
    uprop_elemsize:  int
    uprop_propflags: int  # uint64 (8 bytes)
    uprop_offset:    int  # uint32  byte offset within parent struct
    uprop_base_sz:   int  # sizeof(UProperty) → start of subclass-specific fields
    # UProperty subclasses
    ubyte_enum:     int   # UByteProperty::Enum*
    ubool_bitmask:  int   # UBoolProperty::BitMask (uint32)
    uobjp_propclass: int  # UObjectProperty::PropertyClass*
    ucls_metaclass:  int  # UClassProperty::MetaClass*
    ustrp_struct:    int  # UStructProperty::Struct*
    uarr_inner:      int  # UArrayProperty::Inner*
    umap_keyprop:    int  # UMapProperty::KeyProp*
    umap_valprop:    int  # UMapProperty::ValueProp*
    udel_sigfunc:    int  # UDelegateProperty::SignatureFunction*
    uint_intclass:   int  # UInterfaceProperty::InterfaceClass*
    # Meta
    name_str_off:   int  # offset within FNameEntry to char[]
    name_encoding:  str  # 'ascii' or 'utf-16-le'
    ptr_sz:         int  # 4 (32-bit) or 8 (64-bit)
    # UE4.25+ FField / FProperty support (optional — default False)
    is_ffield:      bool = False  # True → properties are FField not UField
    ustr_child_props: int = 0     # FField* ChildProperties (UE4.25+)
    uffield_next:   int  = 0x18  # FField* Next
    uffield_name:   int  = 0x20  # FName NamePrivate
    uffield_class:  int  = 0x00  # FFieldClass*
    # UE5 FName — has DisplayIndex field making FName 12 bytes (some builds)
    uobj_outer_ue5: int  = 0x20  # UObject* Outer (may be 0x28 on 12-byte FName builds)


# ── UE2 layout (UT2004, Unreal II) ──────────────────────────────────────────
# UObject: VfTable(4)+Index(4)+Unk[20]+Outer(4)+Flags(4)+Name(4)+Class(4)=0x2C
# UField : UObject+SuperField(4)+Next(4)+HashNext(4) = 0x38
# UStruct: UField+Unk[8]+Children(4)+PropSize(4)+Unk[0x3C] = 0x84
# UProperty: UField+ArrayDim(4)+ElemSize(4)+PropFlags(8)+RepOff(2)+RepIdx(2)
#            +Offset(4)+PropLinkNext(4)+CfgLink(4)+CtorLink(4)+RepOwner(4)+Unk[16] = 0x70
UE2_LAYOUT = Layout(
    uobj_outer=0x1C,   uobj_name=0x24,    uobj_class=0x28,
    ufld_next=0x30,    ufld_super=0x2C,
    ustr_children=0x40, ustr_propsize=0x44,
    uenum_names=0x38,  fname_sz=4,
    ufunc_flags=0x84,  ufunc_numparms=0x8D, ufunc_parmsize=0x8E, ufunc_retoff=0x90,
    uprop_arraydim=0x38, uprop_elemsize=0x3C, uprop_propflags=0x40,
    uprop_offset=0x4C, uprop_base_sz=0x70,
    ubyte_enum=0x70,   ubool_bitmask=0x70,
    uobjp_propclass=0x70, ucls_metaclass=0x78,
    ustrp_struct=0x70, uarr_inner=0x70,
    umap_keyprop=0x70, umap_valprop=0x74,
    udel_sigfunc=0x70, uint_intclass=0x70,
    name_str_off=0x0C, name_encoding="utf-16-le", ptr_sz=4,
)

# ── UE3 layout (Hawken, BL2, APB, TribesAscend, UT3 …) ──────────────────────
# UObject: VTable(4)+Unk[28]+Index(4)+Unk[4]+Outer(4)+Name(8)+Class(4)+Archetype(4)=0x3C
# UField : UObject+Next(4) = 0x40
# UStruct: UField+Unk[8]+SuperField(4)+Children(4)+PropSize(4)+Unk[0x30] = 0x84
# UProperty: UField+ArrayDim(4)+ElemSize(4)+PropFlags(8)+RepOff(2)+RepIdx(2)
#            +PropLink(4)+CfgLink(4)+CtorLink(4)+RepOwner(4)+Offset(4)+Unk[12] = 0x74
UE3_LAYOUT = Layout(
    uobj_outer=0x28,   uobj_name=0x2C,    uobj_class=0x34,
    ufld_next=0x3C,    ufld_super=0x48,   # SuperField is in UStruct for UE3
    ustr_children=0x4C, ustr_propsize=0x50,
    uenum_names=0x40,  fname_sz=8,
    ufunc_flags=0x84,  ufunc_numparms=0x95, ufunc_parmsize=0x96, ufunc_retoff=0x98,
    uprop_arraydim=0x40, uprop_elemsize=0x44, uprop_propflags=0x48,
    uprop_offset=0x64, uprop_base_sz=0x74,
    ubyte_enum=0x74,   ubool_bitmask=0x74,
    uobjp_propclass=0x74, ucls_metaclass=0x7C,
    ustrp_struct=0x74, uarr_inner=0x74,
    umap_keyprop=0x74, umap_valprop=0x78,
    udel_sigfunc=0x74, uint_intclass=0x74,
    name_str_off=0x10, name_encoding="ascii", ptr_sz=4,
)

# UE1 — similar to UE2 but Name is at 0x20 and struct sizes differ slightly
# UObject: VfTable(4)+Index(4)+Unk[16]+Outer(4)+Name(4)+Class(4)=0x28
# UField : UObject+SuperField(4)+Next(4)+HashNext(4) = 0x34
# UStruct: UField+Unk[8]+Children(4)+PropSize(4)+... 
# (layout is approximate — UE1 layout wasn't in the reference targets)
UE1_LAYOUT = Layout(
    uobj_outer=0x18,   uobj_name=0x20,    uobj_class=0x24,
    ufld_next=0x2C,    ufld_super=0x28,
    ustr_children=0x38, ustr_propsize=0x3C,
    uenum_names=0x34,  fname_sz=4,
    ufunc_flags=0x74,  ufunc_numparms=0x7D, ufunc_parmsize=0x7E, ufunc_retoff=0x80,
    uprop_arraydim=0x2C, uprop_elemsize=0x30, uprop_propflags=0x34,
    uprop_offset=0x40, uprop_base_sz=0x60,
    ubyte_enum=0x60,   ubool_bitmask=0x60,
    uobjp_propclass=0x60, ucls_metaclass=0x68,
    ustrp_struct=0x60, uarr_inner=0x60,
    umap_keyprop=0x60, umap_valprop=0x64,
    udel_sigfunc=0x60, uint_intclass=0x60,
    name_str_off=0x0C, name_encoding="utf-16-le", ptr_sz=4,
)

# ── UE4 layout (64-bit, UE4.21+, with UE4.25+ FField/FProperty) ─────────────
# UObject: VTable(8)+Flags(4)+Index(4)+Class(8)+Name(8)+Outer(8) = 0x28
# UField : UObject+Next(8) = 0x30
# UStruct: UField+SuperStruct(8)+Children(8)+ChildProperties(8)+PropSize(4) ...
# FFunction: UStruct base(≈0x58)+FunctionFlags(4)+...
# FProperty (extends FField): base FField(0x30)+ArrayDim(4)+ElemSize(4)+PropFlags(8)+Offset(4 at 0x4C)
UE4_LAYOUT = Layout(
    uobj_outer=0x20,    uobj_name=0x18,    uobj_class=0x10,
    ufld_next=0x28,     ufld_super=0x30,
    ustr_children=0x38, ustr_propsize=0x44,
    ustr_child_props=0x40,
    uenum_names=0x40,   fname_sz=8,
    ufunc_flags=0x58,   ufunc_numparms=0x61, ufunc_parmsize=0x62, ufunc_retoff=0x64,
    uprop_arraydim=0x30, uprop_elemsize=0x34, uprop_propflags=0x38,
    uprop_offset=0x4C,  uprop_base_sz=0x70,
    ubyte_enum=0x70,    ubool_bitmask=0x70,
    uobjp_propclass=0x70, ucls_metaclass=0x78,
    ustrp_struct=0x70,  uarr_inner=0x70,
    umap_keyprop=0x70,  umap_valprop=0x78,
    udel_sigfunc=0x70,  uint_intclass=0x70,
    name_str_off=0x10,  name_encoding="ascii",   ptr_sz=8,
    is_ffield=True,
    uffield_next=0x18,  uffield_name=0x20,  uffield_class=0x00,
    uobj_outer_ue5=0x20,
)

# ── UE5 layout (64-bit, UE5.0+) ──────────────────────────────────────────────
# Same UObject layout as UE4.  FNamePool replaces TNameEntryArray for GNames.
# Some UE5 builds use a 12-byte FName (ComparisonIndex+DisplayIndex+Number),
# which shifts Outer to 0x28.  We use the common 8-byte FName default.
UE5_LAYOUT = Layout(
    uobj_outer=0x20,    uobj_name=0x18,    uobj_class=0x10,
    ufld_next=0x28,     ufld_super=0x30,
    ustr_children=0x38, ustr_propsize=0x44,
    ustr_child_props=0x40,
    uenum_names=0x40,   fname_sz=8,
    ufunc_flags=0x58,   ufunc_numparms=0x61, ufunc_parmsize=0x62, ufunc_retoff=0x64,
    uprop_arraydim=0x30, uprop_elemsize=0x34, uprop_propflags=0x38,
    uprop_offset=0x4C,  uprop_base_sz=0x70,
    ubyte_enum=0x70,    ubool_bitmask=0x70,
    uobjp_propclass=0x70, ucls_metaclass=0x78,
    ustrp_struct=0x70,  uarr_inner=0x70,
    umap_keyprop=0x70,  umap_valprop=0x78,
    udel_sigfunc=0x70,  uint_intclass=0x70,
    name_str_off=0x02,  name_encoding="ascii",   ptr_sz=8,
    is_ffield=True,
    uffield_next=0x18,  uffield_name=0x20,  uffield_class=0x00,
    uobj_outer_ue5=0x20,
)

LAYOUTS: Dict[str, Layout] = {
    "UE1": UE1_LAYOUT,
    "UE2": UE2_LAYOUT,
    "UE3": UE3_LAYOUT,
    "UE4": UE4_LAYOUT,
    "UE5": UE5_LAYOUT,
}

# ─────────────────────────────────────────────────────────────────────────────
# Low-level memory helpers
# ─────────────────────────────────────────────────────────────────────────────

def _rptr(backend: MemoryBackend, va: int, is64: bool = False) -> int:
    return backend.rptr(va, is64) or 0

def _ru32(backend: MemoryBackend, va: int) -> int:
    return backend.ru32(va) or 0

def _ru16(backend: MemoryBackend, va: int) -> int:
    raw = backend.read(va, 2)
    if not raw or len(raw) < 2:
        return 0
    return _struct.unpack_from("<H", raw)[0]

def _ru8(backend: MemoryBackend, va: int) -> int:
    raw = backend.read(va, 1)
    if not raw:
        return 0
    return raw[0]

def _ru64(backend: MemoryBackend, va: int) -> int:
    raw = backend.read(va, 8)
    if not raw or len(raw) < 8:
        return 0
    return _struct.unpack_from("<Q", raw)[0]

def _rstr(backend: MemoryBackend, va: int,
          encoding: str = "ascii", max_len: int = 256) -> str:
    raw = backend.read(va, max_len)
    if not raw:
        return ""
    if encoding == "utf-16-le":
        end = -1
        for i in range(0, len(raw) - 1, 2):
            if raw[i] == 0 and raw[i + 1] == 0:
                end = i; break
        raw = raw[:end] if end >= 0 else raw
    else:
        end = raw.find(b"\x00")
        raw = raw[:end] if end >= 0 else raw
    return raw.decode(encoding, errors="replace")

def _valid_name(s: str) -> bool:
    return bool(s) and len(s) < 128 and re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', s) is not None

def _safe_ident(s: str) -> str:
    """Make s a valid C++ identifier."""
    s = re.sub(r'[^A-Za-z0-9_]', '_', s)
    if s and s[0].isdigit():
        s = '_' + s
    return s or "_unknown"

# ─────────────────────────────────────────────────────────────────────────────
# Property-flag constants (same bits across UE1/UE2/UE3)
# ─────────────────────────────────────────────────────────────────────────────
CPF_PARM        = 0x0000_0000_0000_0080
CPF_OUT_PARM    = 0x0000_0000_0000_0100
CPF_RETURN_PARM = 0x0000_0000_0000_0400
CPF_OPTIONAL    = 0x0000_0000_0000_0010

FUNC_STATIC     = 0x00002000
FUNC_NATIVE     = 0x00000400

# ─────────────────────────────────────────────────────────────────────────────
# Data classes (in-memory representation of the parsed object tree)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MemberInfo:
    name:      str
    cpp_type:  str
    offset:    int
    size:      int
    array_dim: int    = 1
    flags:     int    = 0
    bitmask:   int    = 0
    comment:   str    = ""

@dataclass
class ParamInfo:
    name:      str
    cpp_type:  str
    is_out:    bool   = False
    is_return: bool   = False
    is_opt:    bool   = False

@dataclass
class FuncInfo:
    name:       str
    flags:      int
    params:     List[ParamInfo] = field(default_factory=list)
    return_type: str            = "void"
    is_static:  bool            = False

@dataclass
class EnumInfo:
    name:       str
    full_name:  str
    values:     List[str] = field(default_factory=list)

@dataclass
class StructInfo:
    name:       str
    full_name:  str
    cpp_name:   str       # F/U/A prefix + name
    parent:     str       # C++ name of parent class
    size:       int
    members:    List[MemberInfo]       = field(default_factory=list)
    functions:  List[FuncInfo]         = field(default_factory=list)
    is_class:   bool                   = False   # UClass vs UScriptStruct

@dataclass
class PackageData:
    name:    str
    enums:   List[EnumInfo]   = field(default_factory=list)
    structs: List[StructInfo] = field(default_factory=list)   # includes classes

# ─────────────────────────────────────────────────────────────────────────────
# Object database — built from the GObjects dump
# ─────────────────────────────────────────────────────────────────────────────

class ObjectDB:
    """Flat lookup tables built from the GObjects walk."""

    def __init__(self) -> None:
        self.ptr_name:  Dict[int, str] = {}   # obj_ptr → object name
        self.ptr_class: Dict[int, str] = {}   # obj_ptr → class name
        self.ptr_outer: Dict[int, int] = {}   # obj_ptr → outer ptr

    def build(self, backend: MemoryBackend, objects: List[Dict],
              layout: Layout, progress_cb: Optional[Callable] = None) -> None:
        """
        Extend the raw object list with class_ptr and outer_ptr.
        objects is the list from reader.dump_objects() —
        each entry has at least {ptr, name}.
        """
        total = len(objects)
        is64 = layout.ptr_sz == 8
        ptr_fmt = "<Q" if is64 else "<I"
        ptr_read = layout.ptr_sz
        for i, obj in enumerate(objects):
            ptr  = obj.get("ptr", 0)
            name = obj.get("name", "")
            if not ptr:
                continue
            self.ptr_name[ptr] = name
            # Read Outer* and Class* separately (may not be adjacent in UE4)
            outer_ptr = _rptr(backend, ptr + layout.uobj_outer, is64) if is64 else _rptr(backend, ptr + layout.uobj_outer)
            class_ptr = _rptr(backend, ptr + layout.uobj_class, is64) if is64 else _rptr(backend, ptr + layout.uobj_class)
            self.ptr_outer[ptr] = outer_ptr or 0
            obj["_class_ptr"] = class_ptr or 0
            obj["_outer_ptr"] = outer_ptr or 0
            if progress_cb and i % 1000 == 0:
                progress_cb(f"Building object DB: {i:,}/{total:,}")

        # Second pass: resolve class names
        for obj in objects:
            ptr       = obj.get("ptr", 0)
            class_ptr = obj.get("_class_ptr", 0)
            if ptr and class_ptr:
                class_name = self.ptr_name.get(class_ptr, "")
                self.ptr_class[ptr] = class_name

    def get_package_ptr(self, obj_ptr: int) -> int:
        """Walk the Outer chain to find the top-level package ptr."""
        seen: Set[int] = set()
        cur  = obj_ptr
        prev = 0
        while True:
            outer = self.ptr_outer.get(cur, 0)
            if not outer or outer in seen:
                break
            seen.add(cur)
            prev = cur
            cur  = outer
        return cur if cur != obj_ptr else 0

    def get_outer_name(self, obj_ptr: int) -> str:
        outer = self.ptr_outer.get(obj_ptr, 0)
        return self.ptr_name.get(outer, "") if outer else ""

    def get_full_name(self, obj_ptr: int) -> str:
        parts: List[str] = []
        cur = obj_ptr
        seen: Set[int] = set()
        while cur and cur not in seen:
            seen.add(cur)
            n = self.ptr_name.get(cur, "")
            if n:
                parts.insert(0, n)
            cur = self.ptr_outer.get(cur, 0)
        return ".".join(parts)

# ─────────────────────────────────────────────────────────────────────────────
# Property type resolver
# ─────────────────────────────────────────────────────────────────────────────

# Mapping from UE property class name → C++ base type
_SIMPLE_TYPES: Dict[str, str] = {
    "ByteProperty":      "uint8_t",
    "IntProperty":       "int32_t",
    "FloatProperty":     "float",
    "BoolProperty":      "uint32_t",   # real field; bitfield handled separately
    "StrProperty":       "struct FString",
    "NameProperty":      "struct FName",
    "StringProperty":    "struct FString",    # UE1 alias
    "QWordProperty":     "uint64_t",
    "DoubleProperty":    "double",
    "PointerProperty":   "void*",
}


def _resolve_prop_type(backend: MemoryBackend, db: ObjectDB,
                       prop_ptr: int, class_name: str,
                       layout: Layout, depth: int = 0) -> str:
    """Return the C++ type string for a UProperty/FProperty at prop_ptr."""
    if depth > 4:
        return "void*"

    is64 = layout.ptr_sz == 8

    # Normalize FProperty class names to the UProperty equivalents for matching
    # (FByteProperty → ByteProperty, etc.)
    norm = class_name[1:] if class_name.startswith("F") and len(class_name) > 1 and class_name[1].isupper() else class_name

    # Check simple FField types first
    if class_name in _SIMPLE_FFIELD_TYPES:
        cpp = _SIMPLE_FFIELD_TYPES[class_name]
        if class_name == "FByteProperty":
            enum_ptr = _rptr(backend, prop_ptr + layout.ubyte_enum, is64)
            if enum_ptr:
                ename = db.ptr_name.get(enum_ptr, "")
                if _valid_name(ename):
                    cpp = f"TEnumAsByte<enum {_safe_ident(ename)}>"
        return cpp

    if norm in _SIMPLE_TYPES:
        cpp = _SIMPLE_TYPES[norm]
        if norm == "ByteProperty":
            enum_ptr = _rptr(backend, prop_ptr + layout.ubyte_enum, is64)
            if enum_ptr:
                ename = db.ptr_name.get(enum_ptr, "")
                if _valid_name(ename):
                    cpp = f"TEnumAsByte<enum {_safe_ident(ename)}>"
        return cpp

    if norm == "ObjectProperty":
        cls_ptr = _rptr(backend, prop_ptr + layout.uobjp_propclass, is64)
        cls_name = db.ptr_name.get(cls_ptr, "")
        if cls_name and _valid_name(cls_name):
            return f"class {_cpp_prefix(cls_name)}{_safe_ident(cls_name)}*"
        return "class UObject*"

    if norm == "ClassProperty":
        meta_ptr = _rptr(backend, prop_ptr + layout.ucls_metaclass, is64)
        meta_name = db.ptr_name.get(meta_ptr, "")
        if meta_name and _valid_name(meta_name):
            return f"class TSubclassOf<class {_cpp_prefix(meta_name)}{_safe_ident(meta_name)}>"
        return "class UClass*"

    if norm == "StructProperty":
        st_ptr = _rptr(backend, prop_ptr + layout.ustrp_struct, is64)
        st_name = db.ptr_name.get(st_ptr, "")
        if st_name and _valid_name(st_name):
            return f"struct F{_safe_ident(st_name)}"
        return "struct FUnknown"

    if norm == "ArrayProperty":
        inner_ptr = _rptr(backend, prop_ptr + layout.uarr_inner, is64)
        if inner_ptr:
            if layout.is_ffield:
                inner_fclass_ptr = _rptr(backend, inner_ptr + layout.uffield_class, is64)
                inner_class = db.ptr_name.get(inner_fclass_ptr, "")
            else:
                inner_class_ptr = _rptr(backend, inner_ptr + layout.uobj_class, is64)
                inner_class = db.ptr_name.get(inner_class_ptr, "")
            inner_cpp = _resolve_prop_type(backend, db, inner_ptr, inner_class,
                                           layout, depth + 1)
        else:
            inner_cpp = "uint8_t"
        return f"TArray<{inner_cpp}>"

    if norm == "MapProperty":
        k_ptr = _rptr(backend, prop_ptr + layout.umap_keyprop, is64)
        v_ptr = _rptr(backend, prop_ptr + layout.umap_valprop, is64)
        if layout.is_ffield:
            k_cls = db.ptr_name.get(_rptr(backend, k_ptr + layout.uffield_class, is64) if k_ptr else 0, "")
            v_cls = db.ptr_name.get(_rptr(backend, v_ptr + layout.uffield_class, is64) if v_ptr else 0, "")
        else:
            k_cls = db.ptr_name.get(_rptr(backend, k_ptr + layout.uobj_class, is64) if k_ptr else 0, "")
            v_cls = db.ptr_name.get(_rptr(backend, v_ptr + layout.uobj_class, is64) if v_ptr else 0, "")
        kt = _resolve_prop_type(backend, db, k_ptr, k_cls, layout, depth + 1) if k_ptr else "int32_t"
        vt = _resolve_prop_type(backend, db, v_ptr, v_cls, layout, depth + 1) if v_ptr else "int32_t"
        return f"TMap<{kt}, {vt}>"

    if norm == "SetProperty":
        inner_ptr = _rptr(backend, prop_ptr + layout.uarr_inner, is64)
        if inner_ptr:
            cls_off = layout.uffield_class if layout.is_ffield else layout.uobj_class
            inner_class = db.ptr_name.get(_rptr(backend, inner_ptr + cls_off, is64), "")
            inner_cpp = _resolve_prop_type(backend, db, inner_ptr, inner_class, layout, depth + 1)
        else:
            inner_cpp = "uint8_t"
        return f"TSet<{inner_cpp}>"

    if norm == "DelegateProperty":
        sig_ptr = _rptr(backend, prop_ptr + layout.udel_sigfunc, is64)
        sig_name = db.ptr_name.get(sig_ptr, "")
        if sig_name and _valid_name(sig_name):
            return f"struct FScriptDelegate /* {sig_name} */"
        return "struct FScriptDelegate"

    if norm in ("MulticastDelegateProperty", "MulticastInlineDelegateProperty",
                "MulticastSparseDelegateProperty"):
        return "struct FMulticastScriptDelegate"

    if norm == "InterfaceProperty":
        cls_ptr = _rptr(backend, prop_ptr + layout.uint_intclass, is64)
        cls_name = db.ptr_name.get(cls_ptr, "")
        if cls_name and _valid_name(cls_name):
            return f"TScriptInterface<class I{_safe_ident(cls_name)}>"
        return "TScriptInterface<class IInterface>"

    if norm in ("ComponentProperty", "ObjectPropertyBase",
                "SoftObjectProperty", "WeakObjectProperty",
                "LazyObjectProperty"):
        cls_ptr = _rptr(backend, prop_ptr + layout.uobjp_propclass, is64)
        cls_name = db.ptr_name.get(cls_ptr, "")
        prefix = "TSoftObjectPtr" if "Soft" in norm else ""
        if prefix:
            inner = f"class {_cpp_prefix(cls_name)}{_safe_ident(cls_name)}" if cls_name and _valid_name(cls_name) else "class UObject"
            return f"{prefix}<{inner}>"
        if cls_name and _valid_name(cls_name):
            return f"class {_cpp_prefix(cls_name)}{_safe_ident(cls_name)}*"
        return "class UComponent*"

    if norm in ("SoftClassProperty",):
        meta_ptr = _rptr(backend, prop_ptr + layout.ucls_metaclass, is64)
        meta_name = db.ptr_name.get(meta_ptr, "")
        inner = f"class {_cpp_prefix(meta_name)}{_safe_ident(meta_name)}" if meta_name and _valid_name(meta_name) else "class UObject"
        return f"TSoftClassPtr<{inner}>"

    if norm == "EnumProperty":
        enum_ptr = _rptr(backend, prop_ptr + layout.uprop_base_sz + 0x08, is64)
        if enum_ptr:
            ename = db.ptr_name.get(enum_ptr, "")
            if ename and _valid_name(ename):
                return f"TEnumAsByte<enum {_safe_ident(ename)}>"
        return "uint8_t /* enum */"

    if norm == "TextProperty":
        return "struct FText"

    return "uint8_t /* unknown */"


def _cpp_prefix(name: str) -> str:
    """Return 'A' for Actor subclasses, 'U' for other UObject classes."""
    if "Actor" in name:
        return "A"
    return "U"

# ─────────────────────────────────────────────────────────────────────────────
# Struct / class walker
# ─────────────────────────────────────────────────────────────────────────────

_MAX_CHILDREN = 2048   # safety cap on linked-list walk

def _walk_children(backend: MemoryBackend, struct_ptr: int,
                   db: ObjectDB, layout: Layout) -> List[Tuple[int, str, str]]:
    """Return [(child_ptr, class_name, child_name), ...]."""
    is64 = layout.ptr_sz == 8
    first = _rptr(backend, struct_ptr + layout.ustr_children, is64)
    result: List[Tuple[int, str, str]] = []
    seen: Set[int] = set()
    cur = first
    count = 0
    while cur and cur not in seen and count < _MAX_CHILDREN:
        seen.add(cur)
        class_ptr = _rptr(backend, cur + layout.uobj_class, is64)
        class_name = db.ptr_name.get(class_ptr, "")
        child_name = db.ptr_name.get(cur, "")
        result.append((cur, class_name, child_name))
        cur = _rptr(backend, cur + layout.ufld_next, is64)
        count += 1
    return result


def _read_member(backend: MemoryBackend, db: ObjectDB,
                 prop_ptr: int, class_name: str, layout: Layout) -> Optional[MemberInfo]:
    """Read a UProperty and return a MemberInfo."""
    name = db.ptr_name.get(prop_ptr, "")
    if not name:
        return None
    offset    = _ru32(backend, prop_ptr + layout.uprop_offset)
    elem_size = _ru32(backend, prop_ptr + layout.uprop_elemsize)
    array_dim = _ru32(backend, prop_ptr + layout.uprop_arraydim) or 1
    flags     = _ru64(backend, prop_ptr + layout.uprop_propflags)
    bitmask   = 0
    if class_name == "BoolProperty":
        bitmask = _ru32(backend, prop_ptr + layout.ubool_bitmask)
    cpp_type = _resolve_prop_type(backend, db, prop_ptr, class_name, layout)
    size = elem_size * array_dim if elem_size else 0
    return MemberInfo(
        name=_safe_ident(name),
        cpp_type=cpp_type,
        offset=offset,
        size=size,
        array_dim=array_dim,
        flags=flags,
        bitmask=bitmask,
    )


def _read_param(backend: MemoryBackend, db: ObjectDB,
                prop_ptr: int, class_name: str, layout: Layout) -> Optional[ParamInfo]:
    """Read a UProperty that is a function parameter."""
    name  = db.ptr_name.get(prop_ptr, "")
    flags = _ru64(backend, prop_ptr + layout.uprop_propflags)
    if not (flags & CPF_PARM):
        return None
    cpp_type  = _resolve_prop_type(backend, db, prop_ptr, class_name, layout)
    is_return = bool(flags & CPF_RETURN_PARM)
    is_out    = bool(flags & CPF_OUT_PARM) and not is_return
    return ParamInfo(
        name=_safe_ident(name) if name else "retval",
        cpp_type=cpp_type,
        is_out=is_out,
        is_return=is_return,
        is_opt=bool(flags & CPF_OPTIONAL),
    )


def _read_function(backend: MemoryBackend, db: ObjectDB,
                   func_ptr: int, layout: Layout) -> Optional[FuncInfo]:
    name = db.ptr_name.get(func_ptr, "")
    if not name or not _valid_name(name):
        return None
    flags     = _ru32(backend, func_ptr + layout.ufunc_flags)
    params:   List[ParamInfo] = []
    ret_type  = "void"
    # Walk function's children for parameters
    children = _walk_children(backend, func_ptr, db, layout)
    for child_ptr, child_class, _ in children:
        p = _read_param(backend, db, child_ptr, child_class, layout)
        if p is None:
            continue
        if p.is_return:
            ret_type = p.cpp_type
        else:
            params.append(p)
    return FuncInfo(
        name=_safe_ident(name),
        flags=flags,
        params=params,
        return_type=ret_type,
        is_static=bool(flags & FUNC_STATIC),
    )


def _read_enum(backend: MemoryBackend,
               enum_ptr: int, names: Dict[int, str], layout: Layout) -> Optional[EnumInfo]:
    obj_name = names.get(_ru32(backend, enum_ptr + layout.uobj_name), "")
    if not obj_name or not _valid_name(obj_name):
        return None
    is64 = layout.ptr_sz == 8
    # TArray<FName> — read ptr, count
    arr_data  = _rptr(backend, enum_ptr + layout.uenum_names, is64)
    arr_count = _ru32(backend, enum_ptr + layout.uenum_names + layout.ptr_sz)
    values: List[str] = []
    if arr_data and 0 < arr_count < 2048:
        for i in range(arr_count):
            name_idx = _ru32(backend, arr_data + i * layout.fname_sz)
            val_name = names.get(name_idx, f"_{i}")
            values.append(_safe_ident(val_name))
    return EnumInfo(
        name=_safe_ident(obj_name),
        full_name=obj_name,
        values=values,
    )


def _read_struct(backend: MemoryBackend, db: ObjectDB,
                 struct_ptr: int, is_class: bool,
                 layout: Layout) -> Optional[StructInfo]:
    name = db.ptr_name.get(struct_ptr, "")
    if not name or not _valid_name(name):
        return None
    is64 = layout.ptr_sz == 8
    prop_size = _ru32(backend, struct_ptr + layout.ustr_propsize)
    super_ptr = _rptr(backend, struct_ptr + layout.ufld_super, is64)
    parent_cpp = ""
    if super_ptr:
        super_name = db.ptr_name.get(super_ptr, "")
        if super_name and _valid_name(super_name):
            if is_class:
                parent_cpp = f"{_cpp_prefix(super_name)}{_safe_ident(super_name)}"
            else:
                parent_cpp = f"F{_safe_ident(super_name)}"

    # Determine C++ name prefix
    if is_class:
        cpp_name = f"{_cpp_prefix(name)}{_safe_ident(name)}"
    else:
        cpp_name = f"F{_safe_ident(name)}"

    members:   List[MemberInfo] = []
    functions: List[FuncInfo]   = []

    # UE4.25+: properties use FField* ChildProperties; functions still UField* Children
    if layout.is_ffield:
        ffield_children = _walk_ffield_children(backend, struct_ptr, db, layout)
        ufield_children = _walk_children(backend, struct_ptr, db, layout)  # functions only

        prop_children  = [(cp, cc) for (cp, cc, _) in ffield_children if _is_property_class(cc)]
        func_children  = [(cp, cc) for (cp, cc, _) in ufield_children if cc == "Function"]
    else:
        children = _walk_children(backend, struct_ptr, db, layout)
        prop_children = [(cp, cc) for (cp, cc, _) in children if _is_property_class(cc)]
        func_children = [(cp, cc) for (cp, cc, _) in children if cc == "Function"]

    # Sort properties by offset
    prop_with_offset = []
    for (cp, cc) in prop_children:
        off = _ru32(backend, cp + layout.uprop_offset)
        prop_with_offset.append((off, cp, cc))
    prop_with_offset.sort(key=lambda x: x[0])

    # Generate padding for gaps
    cursor = 0
    if parent_cpp:
        # Parent already accounts for the base bytes — start from prop_size of parent
        # We don't know it without reading, so just let the parent handle its bytes
        pass

    pad_id = 0
    for off, cp, cc in prop_with_offset:
        # Add padding if needed
        if off > cursor:
            gap = off - cursor
            members.append(MemberInfo(
                name=f"UnknownData{pad_id:02d}",
                cpp_type="uint8_t",
                offset=cursor,
                size=gap,
                array_dim=gap,
                comment=f"// 0x{cursor:04X}(0x{gap:04X})",
            ))
            pad_id += 1

        m = _read_member(backend, db, cp, cc, layout)
        if m:
            m.comment = f"// 0x{off:04X}(0x{m.size:04X})"
            members.append(m)
            cursor = off + m.size
        else:
            esz = _ru32(backend, cp + layout.uprop_elemsize) or 1
            adm = _ru32(backend, cp + layout.uprop_arraydim) or 1
            cursor = off + esz * adm

    # Trailing padding
    if prop_size and cursor < prop_size:
        gap = prop_size - cursor
        members.append(MemberInfo(
            name=f"UnknownData{pad_id:02d}",
            cpp_type="uint8_t",
            offset=cursor,
            size=gap,
            array_dim=gap,
            comment=f"// 0x{cursor:04X}(0x{gap:04X})",
        ))

    # Functions
    for fp, _ in func_children:
        fi = _read_function(backend, db, fp, layout)
        if fi:
            functions.append(fi)

    return StructInfo(
        name=_safe_ident(name),
        full_name=name,
        cpp_name=cpp_name,
        parent=parent_cpp,
        size=prop_size or 0,
        members=members,
        functions=functions,
        is_class=is_class,
    )


_PROPERTY_CLASSES = {
    "ByteProperty", "IntProperty", "FloatProperty", "BoolProperty",
    "StrProperty", "NameProperty", "StringProperty",
    "ObjectProperty", "ClassProperty", "StructProperty", "ArrayProperty",
    "MapProperty", "DelegateProperty", "InterfaceProperty",
    "ComponentProperty", "ObjectPropertyBase", "QWordProperty",
    "DoubleProperty", "PointerProperty", "WeakObjectProperty",
    "LazyObjectProperty", "AssetObjectProperty",
    # UE4/UE5 FProperty class names (same logical names, 'F' prefix in class, not in FName)
    "FByteProperty", "FIntProperty", "FInt8Property", "FInt16Property",
    "FInt64Property", "FUInt16Property", "FUInt32Property", "FUInt64Property",
    "FFloatProperty", "FDoubleProperty", "FBoolProperty",
    "FStrProperty", "FNameProperty", "FTextProperty",
    "FObjectProperty", "FClassProperty", "FStructProperty", "FArrayProperty",
    "FMapProperty", "FSetProperty", "FDelegateProperty",
    "FMulticastDelegateProperty", "FMulticastInlineDelegateProperty",
    "FMulticastSparseDelegateProperty",
    "FInterfaceProperty", "FSoftObjectProperty", "FSoftClassProperty",
    "FWeakObjectProperty", "FLazyObjectProperty", "FEnumProperty",
    "FFieldPathProperty",
}

def _is_property_class(name: str) -> bool:
    return name in _PROPERTY_CLASSES

# UE4/UE5 FProperty type map (FField class name → C++ type)
_SIMPLE_FFIELD_TYPES: Dict[str, str] = {
    "FByteProperty":     "uint8_t",
    "FIntProperty":      "int32_t",
    "FInt8Property":     "int8_t",
    "FInt16Property":    "int16_t",
    "FInt64Property":    "int64_t",
    "FUInt16Property":   "uint16_t",
    "FUInt32Property":   "uint32_t",
    "FUInt64Property":   "uint64_t",
    "FFloatProperty":    "float",
    "FDoubleProperty":   "double",
    "FBoolProperty":     "uint32_t",
    "FStrProperty":      "struct FString",
    "FNameProperty":     "struct FName",
    "FTextProperty":     "struct FText",
}


def _walk_ffield_children(backend: MemoryBackend, struct_ptr: int,
                          db: ObjectDB, layout: Layout) -> List[Tuple[int, str, str]]:
    """Walk FField* ChildProperties linked list (UE4.25+ properties).

    Returns [(field_ptr, ffield_class_name, field_name), ...]
    """
    is64 = layout.ptr_sz == 8
    first = _rptr(backend, struct_ptr + layout.ustr_child_props, is64)
    result: List[Tuple[int, str, str]] = []
    seen: Set[int] = set()
    cur = first
    count = 0
    while cur and cur not in seen and count < _MAX_CHILDREN:
        seen.add(cur)
        fclass_ptr  = _rptr(backend, cur + layout.uffield_class, is64)
        # FFieldClass: +0x00 uint64 Id, +0x08 FName Name (index into GNames)
        # The name index in FFieldClass::Name lets us look up the class name
        fclass_name_idx = _ru32(backend, fclass_ptr + 0x08) if fclass_ptr else 0
        # We don't have the names dict here; db.ptr_name keyed by ptr, not name index
        # FFieldClass objects are sometimes in ptr_name if they're UObjects — but they
        # are NOT UObjects.  We fall back to reading the FFieldClass' name string
        # directly at a fixed offset (FFieldClass::Name is at +0x08, an FName,
        # and the name string would need GNames to resolve).
        # As a practical approach: FField names come from GNames via FField::NamePrivate.
        # We record the raw name_index and resolve post-hoc via the names dict passed
        # to _read_struct/_read_member etc.
        fclass_name = db.ptr_name.get(fclass_ptr, "")  # empty for non-UObject class ptrs
        # Read FField::NamePrivate index for this field
        field_name_idx = _ru32(backend, cur + layout.uffield_name)
        field_name = ""  # resolve later via names dict
        result.append((cur, fclass_name, field_name))
        cur = _rptr(backend, cur + layout.uffield_next, is64)
        count += 1
    return result

# ─────────────────────────────────────────────────────────────────────────────
# Package builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_packages(backend: MemoryBackend, db: ObjectDB,
                    objects: List[Dict], names: Dict[int, str],
                    layout: Layout,
                    progress_cb: Optional[Callable] = None) -> Dict[str, PackageData]:
    """Walk every object and sort it into its package."""
    packages: Dict[str, PackageData] = {}
    total = len(objects)

    for i, obj in enumerate(objects):
        ptr        = obj.get("ptr", 0)
        class_name = db.ptr_class.get(ptr, "")

        if class_name not in ("Enum", "ScriptStruct", "Class"):
            continue

        # Identify the package (outermost Outer name)
        pkg_ptr  = db.get_package_ptr(ptr)
        pkg_name = db.ptr_name.get(pkg_ptr, "") if pkg_ptr else ""
        if not pkg_name:
            # Fallback: immediate outer
            outer_ptr = db.ptr_outer.get(ptr, 0)
            pkg_name  = db.ptr_name.get(outer_ptr, "Unknown") if outer_ptr else "Unknown"

        if pkg_name not in packages:
            packages[pkg_name] = PackageData(name=pkg_name)
        pkg = packages[pkg_name]

        if class_name == "Enum":
            ei = _read_enum(backend, ptr, names, layout)
            if ei:
                pkg.enums.append(ei)

        elif class_name == "ScriptStruct":
            si = _read_struct(backend, db, ptr, is_class=False, layout=layout)
            if si:
                pkg.structs.append(si)

        elif class_name == "Class":
            si = _read_struct(backend, db, ptr, is_class=True, layout=layout)
            if si:
                pkg.structs.append(si)

        if progress_cb and i % 200 == 0:
            progress_cb(f"Processing packages: {i:,}/{total:,}")

    return packages

# ─────────────────────────────────────────────────────────────────────────────
# Code writer
# ─────────────────────────────────────────────────────────────────────────────

_BASIC_TYPES_HEADER = """\
#pragma once
// Basic Unreal Engine types — auto-generated by UESDKGen

#include <cstdint>
#include <string>
#include <Windows.h>

struct FPointer    {{ uintptr_t Dummy; }};
struct FQWord      {{ int32_t A; int32_t B; }};

struct FName {{
    int32_t Index;
{number_line}\
}};

template<class T>
struct TArray {{
    T*       Data;
    int32_t  Count;
    int32_t  Max;

    T& operator[](int32_t i)       {{ return Data[i]; }}
    const T& operator[](int32_t i) const {{ return Data[i]; }}
    int32_t  Num()   const {{ return Count; }}
    bool     IsValidIndex(int32_t i) const {{ return i < Count; }}
}};

struct FString : TArray<wchar_t> {{
    std::string ToString() const;
}};

struct FText {{
    unsigned char UnknownData[0x18];
}};

struct FScriptDelegate {{
    unsigned char UnknownData[0x0C];
}};

struct FMulticastScriptDelegate {{
    unsigned char UnknownData[0x10];
}};

class UClass;

template<class T>
struct TSubclassOf {{
    UClass* ClassPtr;
}};

template<class T>
struct TScriptInterface {{
    T*     ObjectPointer;
    void*  InterfacePointer;
}};

template<class T>
struct TSoftObjectPtr {{
    unsigned char UnknownData[0x28];
}};

template<class T>
struct TSoftClassPtr {{
    unsigned char UnknownData[0x28];
}};

template<class T>
struct TSet {{
    unsigned char UnknownData[0x50];
}};

template<class K, class V>
struct TMap {{
    unsigned char UnknownData[0x50];
}};

template<class T>
struct TEnumAsByte {{
    uint8_t Value;
    TEnumAsByte() {{}}
    TEnumAsByte(T v) : Value(static_cast<uint8_t>(v)) {{}}
    operator T() const {{ return static_cast<T>(Value); }}
}};
"""

_FILE_HEADER = """\
// {filename}
// {game_name} SDK — auto-generated by UESDKGen
// Engine: {ue_ver}  |  {timestamp}
// DO NOT EDIT — regenerate via UESDKGen
#pragma once

"""


def _write_structs_header(pkg: PackageData, game_short: str,
                          game_name: str, ue_ver: str) -> str:
    lines: List[str] = []
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    fname = f"{game_short}_{pkg.name}_structs.hpp"
    lines.append(_FILE_HEADER.format(
        filename=fname, game_name=game_name, ue_ver=ue_ver, timestamp=ts))
    lines.append(f'#include "../BasicTypes.hpp"\n\n')

    # ── Enums ──────────────────────────────────────────────────────────────
    if pkg.enums:
        lines.append("// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        lines.append("// Enums\n")
        lines.append("// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
        for e in pkg.enums:
            lines.append(f"// {e.full_name}\n")
            lines.append(f"enum {e.name} : uint8_t {{\n")
            for j, v in enumerate(e.values):
                comma = "," if j < len(e.values) - 1 else ""
                lines.append(f"\t{v} = {j}{comma}\n")
            lines.append("};\n\n")

    # ── Structs ─────────────────────────────────────────────────────────────
    script_structs = [s for s in pkg.structs if not s.is_class]
    if script_structs:
        lines.append("// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        lines.append("// Script Structs\n")
        lines.append("// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
        for s in script_structs:
            _append_struct(lines, s, is_class=False)

    return "".join(lines)


def _write_classes_header(pkg: PackageData, game_short: str,
                          game_name: str, ue_ver: str,
                          all_packages: Dict[str, PackageData]) -> str:
    lines: List[str] = []
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    fname = f"{game_short}_{pkg.name}_classes.hpp"
    lines.append(_FILE_HEADER.format(
        filename=fname, game_name=game_name, ue_ver=ue_ver, timestamp=ts))
    lines.append(f'#include "../BasicTypes.hpp"\n')
    lines.append(f'#include "{game_short}_{pkg.name}_structs.hpp"\n\n')

    classes = [s for s in pkg.structs if s.is_class]
    if not classes:
        return "".join(lines)

    # Forward declarations
    lines.append("// ── Forward declarations ──────────────────────────────\n")
    for s in classes:
        lines.append(f"class {s.cpp_name};\n")
    lines.append("\n")

    lines.append("// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    lines.append("// Classes\n")
    lines.append("// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
    for s in classes:
        _append_struct(lines, s, is_class=True)

    return "".join(lines)


def _write_functions_cpp(pkg: PackageData, game_short: str,
                         game_name: str, ue_ver: str) -> str:
    lines: List[str] = []
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"// {game_short}_{pkg.name}_functions.cpp\n")
    lines.append(f"// {game_name} SDK — auto-generated by UESDKGen\n")
    lines.append(f"// Engine: {ue_ver}  |  {ts}\n\n")
    lines.append(f'#include "../../SDK.hpp"\n\n')
    lines.append(f"using namespace {_safe_ident(game_short)}SDK;\n\n")

    classes = [s for s in pkg.structs if s.is_class]
    for cls in classes:
        if not cls.functions:
            continue
        lines.append(f"// ─── {cls.cpp_name} ───\n\n")
        for fn in cls.functions:
            ret  = fn.return_type
            name = fn.name
            args = ", ".join(
                f"{p.cpp_type}{'&' if p.is_out else ''} {p.name}"
                for p in fn.params
            )
            static_kw = "// static\n" if fn.is_static else ""
            lines.append(f"{static_kw}{ret} {cls.cpp_name}::{name}({args})\n")
            lines.append("{\n")
            lines.append("    static UFunction* fn = nullptr;\n")
            lines.append(f'    if (!fn) fn = UObject::FindObject<UFunction>("Function {pkg.name}.{cls.full_name}.{fn.name}");\n')
            lines.append("\n")
            # Build params struct
            if fn.params or ret != "void":
                lines.append(f"    struct {{\n")
                for p in fn.params:
                    lines.append(f"        {p.cpp_type} {p.name};\n")
                if ret != "void":
                    lines.append(f"        {ret} ReturnValue;\n")
                lines.append(f"    }} params;\n")
                for p in fn.params:
                    lines.append(f"    params.{p.name} = {p.name};\n")
                lines.append("\n")
                lines.append("    ProcessEvent(fn, &params);\n")
                if ret != "void":
                    lines.append("    return params.ReturnValue;\n")
            else:
                lines.append("    ProcessEvent(fn, nullptr);\n")
            lines.append("}\n\n")
    return "".join(lines)


def _append_struct(lines: List[str], s: StructInfo, is_class: bool) -> None:
    kw   = "class" if is_class else "struct"
    base = f" : public {s.parent}" if s.parent else ""
    size_comment = f" // 0x{s.size:04X}" if s.size else ""

    lines.append(f"// {s.full_name}\n")
    lines.append(f"// Size: 0x{s.size:04X}\n")
    lines.append(f"{kw} {s.cpp_name}{base}{size_comment}\n{{\n")
    if is_class:
        lines.append("public:\n")

    for m in s.members:
        if m.array_dim > 1:
            decl = f"\t{m.cpp_type} {m.name}[{m.array_dim}];"
        elif m.bitmask:
            decl = f"\tuint32_t {m.name} : 1; // bitmask=0x{m.bitmask:08X}"
        else:
            decl = f"\t{m.cpp_type} {m.name};"
        comment = m.comment if m.comment else f"// 0x{m.offset:04X}"
        lines.append(f"{decl:<60} {comment}\n")

    # Function prototypes
    for fn in s.functions:
        ret  = fn.return_type
        args = ", ".join(
            f"{p.cpp_type}{'&' if p.is_out else ''} {p.name}"
            for p in fn.params
        )
        static_kw = "static " if fn.is_static else ""
        lines.append(f"\n\t{static_kw}{ret} {fn.name}({args});\n")

    lines.append("};\n\n")


def _write_master_header(packages: Dict[str, PackageData],
                         game_short: str, game_name: str, ue_ver: str) -> str:
    lines: List[str] = []
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"// SDK.hpp — {game_name} ({ue_ver}) SDK\n")
    lines.append(f"// Auto-generated by UESDKGen  |  {ts}\n")
    lines.append(f"// {len(packages)} packages\n\n")
    lines.append("#pragma once\n\n")
    lines.append('#include "BasicTypes.hpp"\n\n')
    for pkg_name in sorted(packages.keys()):
        safe = _safe_ident(pkg_name)
        lines.append(f'#include "SDK/{game_short}_{safe}_structs.hpp"\n')
        lines.append(f'#include "SDK/{game_short}_{safe}_classes.hpp"\n')
    return "".join(lines)


def _write_basic_types(layout: Layout, ue_ver: str) -> str:
    number_line = "    int32_t  Number;\n" if layout.fname_sz > 4 else ""
    return _BASIC_TYPES_HEADER.format(number_line=number_line)

# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def generate_sdk_files(
        backend:      MemoryBackend,
        ue_ver:       str,
        names:        Dict[int, str],
        objects:      List[Dict],
        game_name:    str,
        game_short:   str,
        out_dir:      str,
        progress_cb:  Optional[Callable[[str], None]] = None,
) -> Tuple[int, int]:
    """
    Generate a full C++ SDK into *out_dir*/{game_name}/.

    Returns (file_count, package_count).
    """
    def _log(msg: str) -> None:
        if progress_cb:
            progress_cb(msg)

    layout = LAYOUTS.get(ue_ver)
    if not layout:
        _log(f"[!] Unsupported engine version: {ue_ver}")
        return 0, 0

    # ── 1. Output directory ─────────────────────────────────────────────────
    safe_name  = re.sub(r'[^\w\s-]', '', game_name).strip().replace(' ', '_')
    sdk_root   = os.path.join(out_dir, safe_name)
    sdk_subdir = os.path.join(sdk_root, "SDK")
    os.makedirs(sdk_subdir, exist_ok=True)
    _log(f"[*] Output directory: {sdk_root}")

    # ── 2. Build object database ─────────────────────────────────────────────
    _log("[*] Building object database…")
    db = ObjectDB()
    db.build(backend, objects, layout, _log)
    _log(f"[+] Object DB: {len(db.ptr_name):,} objects  "
         f"{len(db.ptr_class):,} classified")

    # ── 3. Walk packages ─────────────────────────────────────────────────────
    _log("[*] Walking packages…")
    packages = _build_packages(backend, db, objects, names, layout, _log)
    _log(f"[+] Found {len(packages):,} packages")
    for pname, pkg in sorted(packages.items()):
        _log(f"    {pname}: {len(pkg.enums)} enums, "
             f"{sum(1 for s in pkg.structs if not s.is_class)} structs, "
             f"{sum(1 for s in pkg.structs if s.is_class)} classes")

    # ── 4. Write BasicTypes.hpp ──────────────────────────────────────────────
    _log("[*] Writing BasicTypes.hpp…")
    with open(os.path.join(sdk_root, "BasicTypes.hpp"), "w", encoding="utf-8") as fh:
        fh.write(_write_basic_types(layout, ue_ver))

    # ── 5. Write per-package files ───────────────────────────────────────────
    file_count = 1   # BasicTypes.hpp
    for pkg_name, pkg in sorted(packages.items()):
        safe_pkg = _safe_ident(pkg_name)
        _log(f"[*] Writing package: {pkg_name}…")

        structs_path = os.path.join(sdk_subdir, f"{game_short}_{safe_pkg}_structs.hpp")
        classes_path = os.path.join(sdk_subdir, f"{game_short}_{safe_pkg}_classes.hpp")
        funcs_path   = os.path.join(sdk_subdir, f"{game_short}_{safe_pkg}_functions.cpp")

        with open(structs_path, "w", encoding="utf-8") as fh:
            fh.write(_write_structs_header(pkg, game_short, game_name, ue_ver))
        with open(classes_path, "w", encoding="utf-8") as fh:
            fh.write(_write_classes_header(pkg, game_short, game_name, ue_ver, packages))
        with open(funcs_path, "w", encoding="utf-8") as fh:
            fh.write(_write_functions_cpp(pkg, game_short, game_name, ue_ver))

        file_count += 3

    # ── 6. Write master SDK.hpp ──────────────────────────────────────────────
    _log("[*] Writing SDK.hpp…")
    with open(os.path.join(sdk_root, "SDK.hpp"), "w", encoding="utf-8") as fh:
        fh.write(_write_master_header(packages, game_short, game_name, ue_ver))
    file_count += 1

    _log(f"[+] SDK generation complete: {file_count} files, "
         f"{len(packages)} packages → {sdk_root}")
    return file_count, len(packages)
