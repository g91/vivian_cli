"""offsets.py — DiscoveredOffsets dataclass for holding auto-detected UE struct offsets.

Python equivalent of Dumper-7's Offsets.h namespace, extended with conversion helpers
for saving discovered layouts as game_data JSON profiles.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any, Dict, Optional

NOT_FOUND: int = -1


@dataclass
class DiscoveredOffsets:
    """All discovered struct offsets from OffsetFinder analysis.

    Fields with value NOT_FOUND (-1) were not detected.
    Default values are filled in by apply_ue4_defaults() / apply_ue5_defaults() / etc.
    """

    # ── UObject ──────────────────────────────────────────────────────────────
    uobj_flags:   int = NOT_FOUND   # EObjectFlags (int32)
    uobj_index:   int = NOT_FOUND   # InternalIndex (int32)
    uobj_class:   int = NOT_FOUND   # UClass* pointer
    uobj_name:    int = NOT_FOUND   # FName.NamePrivate (CompIdx offset)
    uobj_outer:   int = NOT_FOUND   # UObject* Outer

    # ── UField (UE3 / UE4 pre-4.25) ──────────────────────────────────────────
    ufield_next:  int = NOT_FOUND

    # ── FField (UE4.25+) ─────────────────────────────────────────────────────
    ffield_class: int = NOT_FOUND   # FFieldClass*
    ffield_owner: int = NOT_FOUND   # FFieldVariant (16 bytes on 64-bit)
    ffield_next:  int = NOT_FOUND   # FField* Next
    ffield_name:  int = NOT_FOUND   # FName NamePrivate
    ffield_flags: int = NOT_FOUND   # EObjectFlags

    # ── FFieldClass ───────────────────────────────────────────────────────────
    ffieldclass_name:  int = NOT_FOUND  # FName
    ffieldclass_id:    int = NOT_FOUND  # uint64
    ffieldclass_cast:  int = NOT_FOUND  # EClassCastFlags

    # ── UStruct ───────────────────────────────────────────────────────────────
    ustruct_super:      int = NOT_FOUND  # UStruct* SuperStruct
    ustruct_children:   int = NOT_FOUND  # UField* Children
    ustruct_childprops: int = NOT_FOUND  # FField* ChildProperties (4.25+)
    ustruct_size:       int = NOT_FOUND  # int32 PropertiesSize
    ustruct_minalign:   int = NOT_FOUND  # int32 MinAlignment

    # ── UFunction ─────────────────────────────────────────────────────────────
    ufunc_flags:  int = NOT_FOUND   # EFunctionFlags
    ufunc_native: int = NOT_FOUND   # FNativeFuncPtr

    # ── UClass ────────────────────────────────────────────────────────────────
    uclass_castflags:  int = NOT_FOUND  # EClassCastFlags
    uclass_cdo:        int = NOT_FOUND  # ClassDefaultObject
    uclass_interfaces: int = NOT_FOUND  # ImplementedInterfaces TArray

    # ── UEnum ─────────────────────────────────────────────────────────────────
    uenum_names: int = NOT_FOUND    # TArray<TPair<FName,int64>> Names

    # ── UProperty / FProperty ─────────────────────────────────────────────────
    prop_arraydim: int = NOT_FOUND  # int32 ArrayDim
    prop_elemsize: int = NOT_FOUND  # int32 ElementSize
    prop_flags:    int = NOT_FOUND  # EPropertyFlags (uint64)
    prop_offset:   int = NOT_FOUND  # int32 Offset_Internal
    prop_base_sz:  int = NOT_FOUND  # total size of base FProperty

    # ── Property subclasses ───────────────────────────────────────────────────
    byteprop_enum:  int = NOT_FOUND  # UEnum*
    boolprop_base:  int = NOT_FOUND  # FieldSize/ByteOffset/ByteMask/FieldMask block
    objprop_class:  int = NOT_FOUND  # UClass* PropertyClass
    clsprop_meta:   int = NOT_FOUND  # UClass* MetaClass
    strprop_struct: int = NOT_FOUND  # UScriptStruct* Struct
    arrprop_inner:  int = NOT_FOUND  # FProperty* Inner
    mapprop_base:   int = NOT_FOUND  # KeyProp + ValueProp
    setprop_elem:   int = NOT_FOUND  # FProperty* ElementProp
    enumprop_base:  int = NOT_FOUND  # UnderlyingProp + Enum
    delprop_func:   int = NOT_FOUND  # UFunction* SignatureFunction
    intprop_class:  int = NOT_FOUND  # UClass* (InterfaceProperty)

    # ── FName ─────────────────────────────────────────────────────────────────
    fname_sz:          int = 8       # sizeof(FName): 4 (UE1/2) | 8 (UE3+) | 12 (CasePreserving)
    fname_index_off:   int = 0       # ComparisonIndex offset within FName
    fname_number_off:  int = 4       # Number offset within FName

    # ── FNameEntry ────────────────────────────────────────────────────────────
    fname_entry_str_off:    int = 0x10   # offset of char[] within FNameEntry
    fname_entry_encoding:   str = "ascii"
    fname_entry_header_off: int = 0      # uint16 header offset (FNamePool only)

    # ── GObjects / GNames addresses ───────────────────────────────────────────
    gobjects_va:  int = 0
    gnames_va:    int = 0
    gobj_layout:  str = "tarray"
    gnam_layout:  str = "tarray"

    # ── Meta ──────────────────────────────────────────────────────────────────
    is64:         bool = False
    ue_version:   str  = "UE3"
    confidence:   int  = 0
    process_name: str  = ""
    game_name:    str  = ""

    # ─────────────────────────────────────────────────────────────────────────

    def is_valid(self) -> bool:
        """Return True if at minimum the core UObject offsets were found."""
        return self.uobj_class != NOT_FOUND and self.uobj_name != NOT_FOUND

    # ── Default-filling helpers ───────────────────────────────────────────────

    def apply_ue4_defaults(self) -> None:
        """Fill in standard UE4 64-bit hardcoded defaults for any NOT_FOUND fields."""
        defaults = {
            "uobj_flags":  0x08, "uobj_index": 0x0C, "uobj_class": 0x10,
            "uobj_name":   0x18, "uobj_outer": 0x20,
            "ufield_next": 0x28,
            "ffield_class": 0x00, "ffield_owner": 0x08,
            "ffield_next":  0x18, "ffield_name":  0x20, "ffield_flags": 0x28,
            "ffieldclass_name": 0x00, "ffieldclass_id": 0x08,
            "ffieldclass_cast": 0x10,
            "ustruct_super": 0x30, "ustruct_children": 0x38,
            "ustruct_childprops": 0x40, "ustruct_size": 0x44,
            "ustruct_minalign": 0x48,
            "ufunc_flags": 0x58, "ufunc_native": 0xB0,
            "uclass_castflags": 0x98, "uclass_cdo": 0xB8,
            "uclass_interfaces": 0xC8,
            "uenum_names": 0x40,
            "prop_arraydim": 0x30, "prop_elemsize": 0x34,
            "prop_flags": 0x38, "prop_offset": 0x4C, "prop_base_sz": 0x70,
            "byteprop_enum": 0x70, "boolprop_base": 0x70,
            "objprop_class": 0x70, "clsprop_meta": 0x78,
            "strprop_struct": 0x70, "arrprop_inner": 0x70,
            "mapprop_base": 0x70, "setprop_elem": 0x70,
            "enumprop_base": 0x70, "delprop_func": 0x70,
            "intprop_class": 0x70,
            "fname_sz": 8, "fname_entry_str_off": 0x10,
        }
        for attr, val in defaults.items():
            if getattr(self, attr, NOT_FOUND) == NOT_FOUND:
                setattr(self, attr, val)

    def apply_ue5_defaults(self) -> None:
        """Fill in standard UE5 64-bit defaults (mostly same as UE4)."""
        self.apply_ue4_defaults()
        # FNamePool: string starts at +0x02 (after uint16 header)
        if self.fname_entry_str_off == NOT_FOUND:
            self.fname_entry_str_off = 0x02

    def apply_ue3_defaults(self) -> None:
        """Fill in standard UE3 32-bit defaults for any NOT_FOUND fields."""
        defaults_32 = {
            "uobj_flags":  0x08, "uobj_index": 0x0C, "uobj_class": 0x10,
            "uobj_name":   0x20, "uobj_outer": 0x28,
            "ufield_next": 0x30,
            "ustruct_super": 0x38, "ustruct_children": 0x3C,
            "ustruct_size": 0x4C, "ustruct_minalign": 0x50,
            "ufunc_flags": 0x68,
            "uenum_names": 0x40,
            "prop_arraydim": 0x3C, "prop_elemsize": 0x40,
            "prop_flags": 0x48, "prop_offset": 0x4C, "prop_base_sz": 0x60,
            "byteprop_enum": 0x60, "boolprop_base": 0x60,
            "objprop_class": 0x60, "strprop_struct": 0x60,
            "arrprop_inner": 0x60, "mapprop_base": 0x60,
            "setprop_elem": 0x60, "enumprop_base": 0x60, "delprop_func": 0x60,
            "fname_sz": 8, "fname_entry_str_off": 0x10,
        }
        for attr, val in defaults_32.items():
            if getattr(self, attr, NOT_FOUND) == NOT_FOUND:
                setattr(self, attr, val)

    # ── JSON profile export ───────────────────────────────────────────────────

    def to_json_profile(self, key: Optional[str] = None) -> Dict[str, Any]:
        """Convert to the game_data JSON profile format."""
        import re
        safe_key = re.sub(r"[^A-Z0-9_]", "_",
                          (key or self.game_name or "CUSTOM").upper())[:16]

        def _h(v: int) -> Any:
            return hex(v) if v > 0 else v

        return {
            "key":          safe_key,
            "name":         self.game_name or safe_key,
            "ue_version":   self.ue_version,
            "process":      self.process_name,
            "architecture": "x64" if self.is64 else "x86",
            "gobj_layout":  self.gobj_layout,
            "gnam_layout":  self.gnam_layout,
            "gobjects_va":  _h(self.gobjects_va),
            "gnames_va":    _h(self.gnames_va),
            "uobject_offsets": {
                "flags":          self.uobj_flags,
                "internal_index": self.uobj_index,
                "class":          self.uobj_class,
                "name_field_off": self.uobj_name,
                "outer":          self.uobj_outer,
            },
            "ufield_offsets": {
                "next": self.ufield_next,
            },
            "ffield_offsets": {
                "class": self.ffield_class,
                "owner": self.ffield_owner,
                "next":  self.ffield_next,
                "name":  self.ffield_name,
                "flags": self.ffield_flags,
            },
            "fname_layout": {
                "index_off":  self.fname_index_off,
                "number_off": self.fname_number_off,
                "size":       self.fname_sz,
            },
            "fname_entry_offsets": {
                "name_str":      self.fname_entry_str_off,
                "name_encoding": self.fname_entry_encoding,
            },
            "ustruct_offsets": {
                "super":            self.ustruct_super,
                "children":         self.ustruct_children,
                "child_properties": self.ustruct_childprops,
                "size":             self.ustruct_size,
                "min_alignment":    self.ustruct_minalign,
            },
            "ufunction_offsets": {
                "flags":     self.ufunc_flags,
                "native_fn": self.ufunc_native,
            },
            "uclass_offsets": {
                "cast_flags":     self.uclass_castflags,
                "default_object": self.uclass_cdo,
                "interfaces":     self.uclass_interfaces,
            },
            "uenum_offsets": {
                "names": self.uenum_names,
            },
            "uproperty_offsets": {
                "array_dim":       self.prop_arraydim,
                "element_size":    self.prop_elemsize,
                "property_flags":  self.prop_flags,
                "offset_internal": self.prop_offset,
                "base_size":       self.prop_base_sz,
            },
            "property_subclass_offsets": {
                "byte_enum":    self.byteprop_enum,
                "bool_bitmask": self.boolprop_base,
                "obj_class":    self.objprop_class,
                "cls_metaclass": self.clsprop_meta,
                "struct_struct": self.strprop_struct,
                "array_inner":   self.arrprop_inner,
                "map_base":      self.mapprop_base,
                "set_elem":      self.setprop_elem,
                "enum_base":     self.enumprop_base,
                "delegate_fn":   self.delprop_func,
            },
            "confidence":    self.confidence,
            "brute_forced":  True,
            "generated_at":  datetime.datetime.now().isoformat(),
            "notes": (
                f"Auto-generated by UESDKGen brute-forcer — "
                f"{self.ue_version} {'64-bit' if self.is64 else '32-bit'}"
            ),
        }
