"""profiles.py — UE1/UE2/UE3/UE4 game profiles for UESDKGen.

Each profile describes how to find GObjects/GNames for a specific game:
  ue_version      "UE1" | "UE2" | "UE3" | "UE4"
  process         default executable name
  gobj_pattern    byte pattern for scanning
  gobj_mask       'x'/'?' mask matching pattern length
  gobj_off        byte offset from pattern match to the GObjects pointer
  gnam_pattern / gnam_mask / gnam_off — same for GNames
  gobjects_va     known-good hard-coded VA (used when not scanning)
  gnames_va       known-good hard-coded VA
  name_field_off  offset of FName.Index inside UObject
  name_str_off    offset of Name[] inside FNameEntry
  name_encoding   'ascii' (char) or 'utf-16-le' (wchar_t)
  is64            True for x64 builds
  gobj_layout     "tarray" | "fuobj_chunked" | "fuobj_tarray"
  gnam_layout     "tarray" | "chunked"
  gobj_scan_mode  "deref" | "rip" | "rip_deref"
  gnam_scan_mode  "deref" | "rip" | "rip_deref"
  gobj_adjust     pre-scan byte offset added to pattern match (UE4 ARK +12 style)
  gnam_adjust     same for GNames
  notes           human-readable description
"""
from __future__ import annotations

from typing import Dict, Any

# ─────────────────────────────────────────────────────────────────────────────
# Scan patterns — UE1 / UE2 (32-bit, injected into core.dll)
# ─────────────────────────────────────────────────────────────────────────────

# UE1: GNames — MOV EAX, [GlobalNames]  (mov eax, imm32; then indexed into)
_P_UE1_GNAM      = b"\xA1\x00\x00\x00\x00\x8B\x88"
_P_UE1_GNAM_MASK = "x????xx"
_P_UE1_GNAM_OFF  = 0x1    # 4-byte abs addr at match+1

# UE1: GObjects — MOV ECX, [GlobalObjects]; MOV EAX,[ECX+EAX*4]; ADD EBX,EAX; XOR EAX,EAX
_P_UE1_GOBJ      = b"\x8B\x0D\x00\x00\x00\x00\x8B\x04\x81\xC3\x33\xC0"
_P_UE1_GOBJ_MASK = "xx????xxxxxx"
_P_UE1_GOBJ_OFF  = 0x2    # 4-byte abs addr at match+2

# UE2: GObjects ends with RET byte too — slightly longer pattern
_P_UE2_GOBJ      = b"\x8B\x0D\x00\x00\x00\x00\x8B\x04\x81\xC3\x33\xC0\xC3"
_P_UE2_GOBJ_MASK = "xx????xxxxxxx"
_P_UE2_GOBJ_OFF  = 0x2

# ─────────────────────────────────────────────────────────────────────────────
# Scan patterns — UE3 (32-bit, main exe)
# ─────────────────────────────────────────────────────────────────────────────

# Pattern 1  (Section 8, BL2, RL, most shipped UE3 titles)
_P1_GOBJ         = b"\xA1\x00\x00\x00\x00\x8B\x00\x00\x8B\x00\x00\x25\x00\x02\x00\x00"
_P1_GOBJ_MASK    = "x????x??x??xxxxx"
_P1_GOBJ_OFF     = 0x1
_P1_GNAM         = b"\x8b\x0d\x00\x00\x00\x00\x83\x3c\x81\x00\x74"
_P1_GNAM_MASK    = "xx????xxxxx"
_P1_GNAM_OFF     = 0x2

# Pattern 2  (APB, Hawken, TribesAscend, ME3 — different GObjects reg sequence)
_P2_GOBJ         = b"\x8b\x00\x00\x00\x00\x00\x8b\x04\x00\x8b\x40\x00\x25\x00\x02\x00\x00"
_P2_GOBJ_MASK    = "x?????xx?xx?xxxxx"
_P2_GOBJ_OFF     = 0x2
_P2_GNAM         = b"\x8b\x35\x00\x00\x00\x00\x8b\x0d\x00\x00\x00\x00\x83\xc4\x08"
_P2_GNAM_MASK    = "xx????xx????xxx"
_P2_GNAM_OFF     = 0x2

# Pattern 3  (Chivalry, RO2 — P2 GObjects + P1 GNames)
_P3_GOBJ         = _P2_GOBJ
_P3_GOBJ_MASK    = _P2_GOBJ_MASK
_P3_GOBJ_OFF     = _P2_GOBJ_OFF
_P3_GNAM         = _P1_GNAM
_P3_GNAM_MASK    = _P1_GNAM_MASK
_P3_GNAM_OFF     = _P1_GNAM_OFF

# ─────────────────────────────────────────────────────────────────────────────
# Scan patterns — UE4 (64-bit, RIP-relative LEA/MOV)
# All UE4 patterns use RIP-relative addressing:
#   match_va += adjust
#   rip_offset = u32(match_va + 3)
#   target = match_va + 7 + rip_offset
#   gnames_va  = *u64(target)    [rip_deref — MOV GNames, [rip+disp]]
#   gobjects_va = target          [rip       — LEA GObjects, [rip+disp]]
# ─────────────────────────────────────────────────────────────────────────────

# Fortnite / PUBG — GNames MOV [rip+X], rbx
_P_FN_GNAM       = (b"\x48\x89\x1D\x00\x00\x00\x00\x48\x8B\x5C\x24\x00\x48\x83\xC4\x28"
                    b"\xC3\x48\x8B\x5C\x24\x00\x48\x89\x05\x00\x00\x00\x00\x48\x83\xC4"
                    b"\x28\xC3")
_P_FN_GNAM_MASK  = "xxx????xxxx?xxxxxxxxx?xxx????xxxxx"
_P_FN_GNAM_OFF   = 0x3   # RIP displacement at match+3

# Fortnite / PUBG — GObjects LEA rcx, [rip+X]
_P_FN_GOBJ       = (b"\x48\x8D\x05\x00\x00\x00\x00\x48\x89\x01\x33\xC9\x84\xD2\x41\x8B"
                    b"\x40\x08\x49\x89\x48\x10\x0F\x45\x05\x00\x00\x00\x00\xFF\xC0\x49"
                    b"\x89\x48\x10\x41\x89\x40\x08")
_P_FN_GOBJ_MASK  = "xxx????xxxxxxxxxxxxxxxxxx????xxxxxxxxxx"
_P_FN_GOBJ_OFF   = 0x3

# ARK / AloneInTheDark — GNames (pre-adjust +12 or +5)
_P_ARK_GNAM      = b"\x48\x89\x83\x00\x00\x00\x00\xE8\x00\x00\x00\x00\x48\x89\x1D"
_P_ARK_GNAM_MASK = "xxx????x????xxx"
_P_ARK_GNAM_OFF  = 0x3   # RIP disp is 12 bytes later (adjust=12)

_P_AITD_GNAM     = b"\x48\x8B\x5C\x24\x00\x48\x89\x05\x00\x00\x00\x00\x48\x83\xC4\x28\xC3"
_P_AITD_GNAM_MASK = "xxxx?xxx????xxxxx"
_P_AITD_GNAM_OFF  = 0x3   # pre-adjust = 5

# ARK / AITD — GObjects LEA rax, [rip+X]
_P_ARK_GOBJ      = b"\x48\x8D\x05\x00\x00\x00\x00\x45\x84\xC0\x48\x89\x01"
_P_ARK_GOBJ_MASK = "xxx????xxxxxx"
_P_ARK_GOBJ_OFF  = 0x3

_P_AITD_GOBJ     = b"\x48\x8D\x15\x00\x00\x00\x00\x41\x8B\xF9"
_P_AITD_GOBJ_MASK = "xxx????xxx"
_P_AITD_GOBJ_OFF  = 0x3

# Paragon — GNames MOV [rip+X], r__ / GObjects LEA rdx, [rip+X]
_P_PAR_GNAM      = b"\x48\x89\x05\x00\x00\x00\x00\x48\x83\xC4\x28\xC3\xE9"
_P_PAR_GNAM_MASK = "xxx????xxxxxx"
_P_PAR_GNAM_OFF  = 0x3

_P_PAR_GOBJ      = b"\x48\x8D\x15\x00\x00\x00\x00\x48\x8D\x4C\x24\x00\x45\x8B\xFE"
_P_PAR_GOBJ_MASK = "xxx????xxxx?xxx"
_P_PAR_GOBJ_OFF  = 0x3

# UT4 — GNames (in UE4-Core-Win64-Shipping.dll)
_P_UT4_GNAM      = b"\x48\x8B\x1D\x00\x00\x00\x00\x48\x85\xDB\x75\x35"
_P_UT4_GNAM_MASK = "xxx????xxxxx"
_P_UT4_GNAM_OFF  = 0x3

# UT4 — GObjects (in UE4-CoreUObject-Win64-Shipping.dll)
_P_UT4_GOBJ      = b"\x48\x8D\x0D\x00\x00\x00\x00\xC6\x05"
_P_UT4_GOBJ_MASK = "xxx????xx"
_P_UT4_GOBJ_OFF  = 0x3

# ─────────────────────────────────────────────────────────────────────────────
# ProcessEvent VTable-scan patterns
# Scanned inside each vtable slot's function body to find ProcessEvent and
# determine its vtable index.
# pe_thiscall=True  → 32-bit __thiscall convention (UE1/UE2/UE3)
# pe_thiscall=False → 64-bit fastcall (UE4)
# pe_extra_null     → function takes an extra void* nullptr 4th arg (UE2/RL)
# ─────────────────────────────────────────────────────────────────────────────

# UE3 standard (BL2, Hawken, TA, UT3, RL, S8, and most UE3 titles)
_P_PE_UE3        = b"\x74\x00\x83\xC0\x07\x83\xE0\xF8\xE8\x00\x00\x00\x00\x8B\xC4"
_P_PE_UE3_MASK   = "x?xxxxxxx????xx"

# UE4 standard (Paragon, PUBG, UT4, AloneInTheDark)
_P_PE_UE4_STD      = b"\x45\x33\xF6\x4D\x8B\xE0"
_P_PE_UE4_STD_MASK = "xxxxxx"

# UE4 ARK: Survival Evolved
_P_PE_UE4_ARK      = b"\x48\x89\x85\x00\x00\x00\x00\x8B\x41\x08\x33\xFF"
_P_PE_UE4_ARK_MASK = "xxx????xxxxx"

# UE4 Fortnite
_P_PE_UE4_FN       = b"\x45\x33\xF6\x3B\x05\x00\x00\x00\x00\x4D\x8B\xE0"
_P_PE_UE4_FN_MASK  = "xxxxx????xxx"

# UE2 Unreal Tournament 2004
_P_PE_UE2_UT2004      = b"\xA1\x00\x00\x00\x00\x85\xC0\x53\x56\x57\x8B"
_P_PE_UE2_UT2004_MASK = "x????xxxxxx"

# UE2 Unreal 2
_P_PE_UE2_U2      = b"\x33\xF6\x89\x65\xF0\x89\x4D\xEC\x89\x75\xFC\x0F\x31"
_P_PE_UE2_U2_MASK = "xxxxxxxxxxxxx"

# ─────────────────────────────────────────────────────────────────────────────
# Common struct offsets per UE generation
# ─────────────────────────────────────────────────────────────────────────────

# UE1 — 32-bit; FName is just Index (int32); name at FNameEntry+0x0C (wchar_t)
# UObject layout: VTable(4) + InternalIndex(4) + Unk(0x10) + Outer(4) + Unk(4) + Name(4) @ 0x20
_OFF_UE1 = dict(
    ue_version     = "UE1",
    name_field_off = 0x20,
    name_str_off   = 0x0C,
    name_encoding  = "utf-16-le",
    is64           = False,
    gobj_layout    = "tarray",
    gnam_layout    = "tarray",
    gobj_scan_mode = "deref",
    gnam_scan_mode = "deref",
    gobj_adjust    = 0,
    gnam_adjust    = 0,
)

# UE2 — 32-bit; same UObject layout as UE1; UStruct has different padding
_OFF_UE2 = {**_OFF_UE1, "ue_version": "UE2"}

# UE3 — 32-bit; FName = {Index, Number}; name at FNameEntry+0x10 (ASCII or wide)
# UObject layout: VTable(4)+InternalIndex(4)+Unk(0x20)+Outer(4)+Name(8) @ 0x2C
_OFF32 = dict(
    ue_version     = "UE3",
    name_field_off = 0x2C,
    name_str_off   = 0x10,
    name_encoding  = "ascii",
    is64           = False,
    gobj_layout    = "tarray",
    gnam_layout    = "tarray",
    gobj_scan_mode = "deref",
    gnam_scan_mode = "deref",
    gobj_adjust    = 0,
    gnam_adjust    = 0,
)

# UE4 — 64-bit; FUObjectArray (chunked); TStaticIndirectArray (GNames)
# UObject layout: Vtable(8)+Flags(4)+InternalIndex(4)+Class(8)+Name(8) @ 0x18
_OFF_UE4 = dict(
    ue_version     = "UE4",
    name_field_off = 0x18,
    name_str_off   = 0x10,
    name_encoding  = "ascii",
    is64           = True,
    gobj_layout    = "fuobj_chunked",
    gnam_layout    = "chunked",
    gobj_scan_mode = "rip",
    gnam_scan_mode = "rip_deref",
    gobj_adjust    = 0,
    gnam_adjust    = 0,
)

# UE4 variant where GObjects is a FUObjectArray holding a TArray<UObject*>
# (ARK, AloneInTheDark — older UE4 builds)
_OFF_UE4_TARRAY = {**_OFF_UE4, "gobj_layout": "fuobj_tarray"}

# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# Game profiles
# ─────────────────────────────────────────────────────────────────────────────
GAME_PROFILES: Dict[str, Dict[str, Any]] = {

    # ── Custom / unknown game (brute-force mode) ────────────────────────────
    "CUSTOM": {
        "name":         "Custom / Unknown",
        "process":      "",
        "gobj_pattern": None, "gobj_mask": "", "gobj_off": 0,
        "gnam_pattern": None, "gnam_mask": "", "gnam_off": 0,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Custom game — select process from list, then use Brute Force to discover.",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Unreal Engine 1 (1998-2000)
    # ═══════════════════════════════════════════════════════════════════════

    "UE1_UNREAL": {
        "name":         "Unreal / Unreal Gold (UE1)",
        "process":      "Unreal.exe",
        "gobj_pattern": _P_UE1_GOBJ, "gobj_mask": _P_UE1_GOBJ_MASK, "gobj_off": _P_UE1_GOBJ_OFF,
        "gnam_pattern": _P_UE1_GNAM, "gnam_mask": _P_UE1_GNAM_MASK, "gnam_off": _P_UE1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF_UE1,
        "notes": "Unreal / Unreal Gold (1998). UE1. core.dll. FNameEntry: 0x0C unk + wchar_t Data[0x10]. FName=int32 Index only.",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Unreal Engine 2 (2002-2004)
    # ═══════════════════════════════════════════════════════════════════════

    "UE2_UT2004": {
        "name":         "Unreal Tournament 2004 (UE2)",
        "process":      "UT2004.exe",
        "gobj_pattern": _P_UE2_GOBJ, "gobj_mask": _P_UE2_GOBJ_MASK, "gobj_off": _P_UE2_GOBJ_OFF,
        "gnam_pattern": _P_UE1_GNAM, "gnam_mask": _P_UE1_GNAM_MASK, "gnam_off": _P_UE1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF_UE2,
        "notes": "Unreal Tournament 2004. UE2. core.dll. GObjects pattern has trailing RET byte.",
    },

    "UE2_UNREAL2": {
        "name":         "Unreal II: The Awakening (UE2)",
        "process":      "Unreal2.exe",
        "gobj_pattern": _P_UE2_GOBJ, "gobj_mask": _P_UE2_GOBJ_MASK, "gobj_off": _P_UE2_GOBJ_OFF,
        "gnam_pattern": _P_UE1_GNAM, "gnam_mask": _P_UE1_GNAM_MASK, "gnam_off": _P_UE1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF_UE2,
        "notes": "Unreal II: The Awakening (2003). UE2. core.dll. UStruct has +8 unknown padding.",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Unreal Engine 3 (2006-2014) — 32-bit titles
    # ═══════════════════════════════════════════════════════════════════════

    "S8": {
        "name":         "Section 8 / Prejudice",
        "process":      "S8Game-F.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x013B9B78,
        "gnames_va":    0x01377868,
        **_OFF32,
        "notes": "Section 8 + Section 8: Prejudice (S8/S9). UE3 Pattern1.",
    },

    "S9": {
        "name":         "Section 8: Prejudice",
        "process":      "S8Game-F.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x013B9B78,
        "gnames_va":    0x01377868,
        **_OFF32,
        "notes": "Section 8: Prejudice standalone launch variant.",
    },

    "AA3": {
        "name":         "America's Army 3",
        "process":      "AA3Game-Win32-Shipping.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "America's Army 3. UE3 Pattern1.",
    },

    "APB": {
        "name":         "APB: Reloaded",
        "process":      "APB.exe",
        "gobj_pattern": _P2_GOBJ,  "gobj_mask": _P2_GOBJ_MASK, "gobj_off": _P2_GOBJ_OFF,
        "gnam_pattern": _P2_GNAM,  "gnam_mask": _P2_GNAM_MASK, "gnam_off": _P2_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "APB: All Points Bulletin / Reloaded. UE3 Pattern2. FNameEntry has Flags-based NamePtr variant.",
    },

    "BLR": {
        "name":         "Blacklight: Retribution",
        "process":      "BLR.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Blacklight: Retribution. UE3 Pattern1.",
    },

    "BL2": {
        "name":         "Borderlands 2",
        "process":      "Borderlands2.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Borderlands 2 (Gearbox/2K). UE3 Pattern1. FNameEntry: 0x10 unk + char Name[1024].",
    },

    "BR": {
        "name":         "Brink",
        "process":      "Brink.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Brink (Splash Damage). UE3 Pattern1.",
    },

    "CC": {
        "name":         "Chivalry: Medieval Warfare",
        "process":      "UDKGame-Win32-Shipping.exe",
        "gobj_pattern": _P3_GOBJ,  "gobj_mask": _P3_GOBJ_MASK, "gobj_off": _P3_GOBJ_OFF,
        "gnam_pattern": _P3_GNAM,  "gnam_mask": _P3_GNAM_MASK, "gnam_off": _P3_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Chivalry: Medieval Warfare / Deadliest Warrior. UE3 Pattern3.",
    },

    "GA": {
        "name":         "Guns of Icarus Online",
        "process":      "UDKGame-Win32-Shipping.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Guns of Icarus Online. UE3 Pattern1.",
    },

    "HF": {
        "name":         "Hawken",
        "process":      "UDKGame-Win32-Shipping.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Hawken. UE3 Pattern1. FNameEntry: uint64_t Flags+Index+HashNext+union{Ansi,Wide}@0x10. IsWide=(Index&1).",
    },

    "ME3": {
        "name":         "Mass Effect 3",
        "process":      "MassEffect3.exe",
        "gobj_pattern": _P2_GOBJ,  "gobj_mask": _P2_GOBJ_MASK, "gobj_off": _P2_GOBJ_OFF,
        "gnam_pattern": _P2_GNAM,  "gnam_mask": _P2_GNAM_MASK, "gnam_off": _P2_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Mass Effect 3 (UE3). UE3 Pattern2.",
    },

    "ODB": {
        "name":         "Orcs Must Die",
        "process":      "OrcsMustDie.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Orcs Must Die. UE3 Pattern1.",
    },

    "R6V2": {
        "name":         "Rainbow Six: Vegas 2",
        "process":      "RainbowSixVegas2_Game.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Rainbow Six: Vegas 2. UE3 Pattern1.",
    },

    "RD": {
        "name":         "Ravaged",
        "process":      "UDKGame-Win32-Shipping.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Ravaged (2012). UE3 Pattern1.",
    },

    "RL": {
        "name":         "Rocket League",
        "process":      "RocketLeague.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Rocket League (Psyonix). UE3 Pattern1. FNameEntry: uint64_t Flags+Index+HashNext+Ansi@0x10. IsWide=Index&1.",
    },

    "RO2": {
        "name":         "Red Orchestra 2",
        "process":      "ROGame.exe",
        "gobj_pattern": _P3_GOBJ,  "gobj_mask": _P3_GOBJ_MASK, "gobj_off": _P3_GOBJ_OFF,
        "gnam_pattern": _P3_GNAM,  "gnam_mask": _P3_GNAM_MASK, "gnam_off": _P3_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Red Orchestra 2: Heroes of Stalingrad. UE3 Pattern3.",
    },

    "SMNC": {
        "name":         "Super Monday Night Combat",
        "process":      "UDKGame-Win32-Shipping.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Super Monday Night Combat. UE3 Pattern1.",
    },

    "SOTL": {
        "name":         "Sang-Froid: Tales of Werewolves",
        "process":      "UDKGame-Win32-Shipping.exe",
        "gobj_pattern": _P2_GOBJ,  "gobj_mask": _P2_GOBJ_MASK, "gobj_off": _P2_GOBJ_OFF,
        "gnam_pattern": _P2_GNAM,  "gnam_mask": _P2_GNAM_MASK, "gnam_off": _P2_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Sang-Froid: Tales of Werewolves. UE3 Pattern2.",
    },

    "ST": {
        "name":         "Sanctum",
        "process":      "UDKGame-Win32-Shipping.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Sanctum. UE3 Pattern1.",
    },

    "TA": {
        "name":         "Tribes: Ascend",
        "process":      "TribesAscend.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Tribes: Ascend (Hi-Rez). UE3 Pattern1. FNameEntry: uint64_t Flags+Index+HashNext+Ansi/Wide@0x10.",
    },

    "TE": {
        "name":         "Trine",
        "process":      "Trine.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Trine. UE3 Pattern1.",
    },

    "UT3": {
        "name":         "Unreal Tournament 3",
        "process":      "UT3.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "name_encoding": "utf-16-le",   # FNameEntry: wchar_t WideName[1024] @ 0x10
        "notes": "Unreal Tournament 3. UE3 Pattern1. FNameEntry: uint32_t Index+0x0C unk+wchar_t WideName[1024]@0x10. Wide names.",
    },

    "UDK": {
        "name":         "Generic UDK / UE3",
        "process":      "UDKGame-Win32-Shipping.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Generic UDK / UE3 fallback.",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # Unreal Engine 4 (2014+) — 64-bit titles
    # GNames: TStaticIndirectArrayThreadSafeRead (128 chunks x 16384 entries)
    # GObjects: FUObjectArray (chunked TUObjectArray or TArray<UObject*>)
    # Pattern scan: RIP-relative LEA/MOV — scan_mode rip / rip_deref
    # ═══════════════════════════════════════════════════════════════════════

    "ARK": {
        "name":         "ARK: Survival Evolved (UE4)",
        "process":      "ShooterGame.exe",
        "gobj_pattern": _P_ARK_GOBJ, "gobj_mask": _P_ARK_GOBJ_MASK, "gobj_off": _P_ARK_GOBJ_OFF,
        "gnam_pattern": _P_ARK_GNAM, "gnam_mask": _P_ARK_GNAM_MASK, "gnam_off": _P_ARK_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF_UE4_TARRAY,
        "gnam_adjust":  12,
        "notes": "ARK: Survival Evolved. UE4 x64. GObjects=FUObjectArray+TArray<UObject*>. GNames pre-adjust=12.",
    },

    "AITD": {
        "name":         "Alone in the Dark: Illumination (UE4)",
        "process":      "AloneInTheDark.exe",
        "gobj_pattern": _P_AITD_GOBJ, "gobj_mask": _P_AITD_GOBJ_MASK, "gobj_off": _P_AITD_GOBJ_OFF,
        "gnam_pattern": _P_AITD_GNAM, "gnam_mask": _P_AITD_GNAM_MASK, "gnam_off": _P_AITD_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF_UE4_TARRAY,
        "gnam_adjust":  5,
        "notes": "Alone in the Dark: Illumination. UE4 x64. GObjects=FUObjectArray+TArray. GNames pre-adjust=5.",
    },

    "FN": {
        "name":         "Fortnite (UE4)",
        "process":      "FortniteClient-Win64-Shipping.exe",
        "gobj_pattern": _P_FN_GOBJ, "gobj_mask": _P_FN_GOBJ_MASK, "gobj_off": _P_FN_GOBJ_OFF,
        "gnam_pattern": _P_FN_GNAM, "gnam_mask": _P_FN_GNAM_MASK, "gnam_off": _P_FN_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF_UE4,
        "notes": "Fortnite (Epic). UE4 x64. GObjects=FUObjectArray+TUObjectArray. FUObjectItem.sizeof=0x18.",
    },

    "PUBG": {
        "name":         "PUBG (UE4)",
        "process":      "TslGame.exe",
        "gobj_pattern": _P_FN_GOBJ, "gobj_mask": _P_FN_GOBJ_MASK, "gobj_off": _P_FN_GOBJ_OFF,
        "gnam_pattern": _P_FN_GNAM, "gnam_mask": _P_FN_GNAM_MASK, "gnam_off": _P_FN_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF_UE4,
        "notes": "PUBG / PlayerUnknown's Battlegrounds. UE4 x64. Same pattern set as Fortnite.",
    },

    "PAR": {
        "name":         "Paragon (UE4)",
        "process":      "Paragon-Win64-Shipping.exe",
        "gobj_pattern": _P_PAR_GOBJ, "gobj_mask": _P_PAR_GOBJ_MASK, "gobj_off": _P_PAR_GOBJ_OFF,
        "gnam_pattern": _P_PAR_GNAM, "gnam_mask": _P_PAR_GNAM_MASK, "gnam_off": _P_PAR_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF_UE4,
        "notes": "Paragon (Epic Games, shut down 2018). UE4 x64.",
    },

    "UT4": {
        "name":         "Unreal Tournament 4 (UE4)",
        "process":      "UE4Game-Win64-Shipping.exe",
        "gobj_pattern": _P_UT4_GOBJ, "gobj_mask": _P_UT4_GOBJ_MASK, "gobj_off": _P_UT4_GOBJ_OFF,
        "gnam_pattern": _P_UT4_GNAM, "gnam_mask": _P_UT4_GNAM_MASK, "gnam_off": _P_UT4_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF_UE4,
        "notes": "Unreal Tournament 4/2016. UE4 x64. GNames in UE4-Core dll, GObjects in UE4-CoreUObject dll.",
    },
}

# Ordered list for the UI combo-box
# UE3 first (S8 as default), then UE1, UE2, UE4, CUSTOM last
_UE1_KEYS  = sorted(k for k, v in GAME_PROFILES.items() if v.get("ue_version") == "UE1")
_UE2_KEYS  = sorted(k for k, v in GAME_PROFILES.items() if v.get("ue_version") == "UE2")
_UE3_KEYS  = sorted(k for k, v in GAME_PROFILES.items()
                    if v.get("ue_version") == "UE3" and k not in ("S8", "CUSTOM"))
_UE4_KEYS  = sorted(k for k, v in GAME_PROFILES.items() if v.get("ue_version") == "UE4")

PROFILE_KEYS = ["S8"] + _UE3_KEYS + _UE1_KEYS + _UE2_KEYS + _UE4_KEYS + ["CUSTOM"]

DEFAULT_PROFILE = "S8"

# ─────────────────────────────────────────────────────────────────────────────
# ProcessEvent vtable detection fields — merged into each profile after the fact
# so the profile dicts above stay focused on GObjects/GNames scanning.
#
# pe_pattern      byte string to match inside a vtable slot's function body
# pe_mask         'x'/'?' character mask (same length as pe_pattern)
# pe_scan_limit   maximum vtable entries to walk (as entry count, not byte offset)
# pe_thiscall     True = 32-bit __thiscall; False = 64-bit fastcall (UE4)
# pe_extra_null   True = ProcessEvent takes an extra void* nullptr 4th argument
# ─────────────────────────────────────────────────────────────────────────────
_PE_NONE      = dict(pe_pattern=None, pe_mask="", pe_scan_limit=0,
                     pe_thiscall=True, pe_extra_null=False)
_PE_UE3_200   = dict(pe_pattern=_P_PE_UE3, pe_mask=_P_PE_UE3_MASK,
                     pe_scan_limit=0x200, pe_thiscall=True, pe_extra_null=False)
_PE_UE3_280   = dict(pe_pattern=_P_PE_UE3, pe_mask=_P_PE_UE3_MASK,
                     pe_scan_limit=0x280, pe_thiscall=True, pe_extra_null=False)
_PE_RL        = dict(pe_pattern=_P_PE_UE3, pe_mask=_P_PE_UE3_MASK,
                     pe_scan_limit=0x280, pe_thiscall=True, pe_extra_null=True)
_PE_UE4_STD   = dict(pe_pattern=_P_PE_UE4_STD, pe_mask=_P_PE_UE4_STD_MASK,
                     pe_scan_limit=0x200, pe_thiscall=False, pe_extra_null=False)
_PE_UE4_ARK   = dict(pe_pattern=_P_PE_UE4_ARK, pe_mask=_P_PE_UE4_ARK_MASK,
                     pe_scan_limit=0x200, pe_thiscall=False, pe_extra_null=False)
_PE_UE4_FN    = dict(pe_pattern=_P_PE_UE4_FN, pe_mask=_P_PE_UE4_FN_MASK,
                     pe_scan_limit=0x200, pe_thiscall=False, pe_extra_null=False)
_PE_UT2004    = dict(pe_pattern=_P_PE_UE2_UT2004, pe_mask=_P_PE_UE2_UT2004_MASK,
                     pe_scan_limit=0x200, pe_thiscall=True, pe_extra_null=True)
_PE_U2        = dict(pe_pattern=_P_PE_UE2_U2, pe_mask=_P_PE_UE2_U2_MASK,
                     pe_scan_limit=0x200, pe_thiscall=True, pe_extra_null=True)

_PE_MAP: Dict[str, Dict[str, Any]] = {
    # UE1 — Unreal has no virtualFunctionPattern (inline only)
    "UE1_UNREAL": _PE_NONE,
    # UE2
    "UE2_UT2004":  _PE_UT2004,
    "UE2_UNREAL2": _PE_U2,
    # UE3 standard (scan_limit=0x200)
    "S8":    _PE_UE3_200, "S9":   _PE_UE3_200, "AA3":  _PE_UE3_200,
    "BLR":   _PE_UE3_200, "BL2":  _PE_UE3_200, "BR":   _PE_UE3_200,
    "CC":    _PE_UE3_200, "GA":   _PE_UE3_200, "HF":   _PE_UE3_200,
    "ME3":   _PE_UE3_200, "ODB":  _PE_UE3_200, "R6V2": _PE_UE3_200,
    "RD":    _PE_UE3_200, "RO2":  _PE_UE3_200, "SMNC": _PE_UE3_200,
    "SOTL":  _PE_UE3_200, "ST":   _PE_UE3_200, "TA":   _PE_UE3_200,
    "TE":    _PE_UE3_200, "UDK":  _PE_UE3_200,
    # UE3 extended scan (scan_limit=0x280)
    "UT3":   _PE_UE3_280,
    # RL uses 0x280 + extra nullptr arg
    "RL":    _PE_RL,
    # APB has no virtualFunctionPattern (custom inline fn, no sig)
    "APB":   _PE_NONE,
    # UE4
    "ARK":   _PE_UE4_ARK,
    "AITD":  _PE_UE4_STD,
    "FN":    _PE_UE4_FN,
    "PUBG":  _PE_UE4_STD,
    "PAR":   _PE_UE4_STD,
    "UT4":   _PE_UE4_STD,
    # Brute-force / unknown
    "CUSTOM": _PE_NONE,
}

# Merge ProcessEvent detection fields into every profile
for _pkey, _peval in _PE_MAP.items():
    if _pkey in GAME_PROFILES:
        GAME_PROFILES[_pkey].update(_peval)
del _pkey, _peval