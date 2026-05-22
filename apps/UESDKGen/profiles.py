"""profiles.py — UE3 game profiles for UESDKGen.

Each profile describes how to find GObjects/GNames for a specific game:
  process         default executable name
  gobj_pattern    byte pattern for scanning
  gobj_mask       'x'/'?' mask matching pattern length
  gobj_off        byte offset from pattern match to the GObjects pointer
  gname_pattern / gname_mask / gname_off — same for GNames
  gobjects_va     known-good hard-coded VA (used when not scanning)
  gnames_va       known-good hard-coded VA
  name_field_off  offset of FName.dwIndex inside UObject
  name_str_off    offset of Name[] inside FNameEntry
  name_encoding   'ascii' (char) or 'utf-16-le' (wchar_t)
  is64            True for x64 builds
  notes           human-readable description
"""
from __future__ import annotations

from typing import Dict, Any

# ─────────────────────────────────────────────────────────────────────────────
# Pattern bytes — shared across games
# ─────────────────────────────────────────────────────────────────────────────

# Pattern 1  (S8, most common UE3 games)
_P1_GOBJ         = b"\xA1\x00\x00\x00\x00\x8B\x00\x00\x8B\x00\x00\x25\x00\x02\x00\x00"
_P1_GOBJ_MASK    = "x????x??x??xxxxx"
_P1_GOBJ_OFF     = 0x1
_P1_GNAM         = b"\x8b\x0d\x00\x00\x00\x00\x83\x3c\x81\x00\x74"
_P1_GNAM_MASK    = "xx????xxxxx"
_P1_GNAM_OFF     = 0x2

# Pattern 2  (alternative GObjects layout)
_P2_GOBJ         = b"\x8b\x00\x00\x00\x00\x00\x8b\x04\x00\x8b\x40\x00\x25\x00\x02\x00\x00"
_P2_GOBJ_MASK    = "x?????xx?xx?xxxxx"
_P2_GOBJ_OFF     = 0x2
_P2_GNAM         = b"\x8b\x35\x00\x00\x00\x00\x8b\x0d\x00\x00\x00\x00\x83\xc4\x08"
_P2_GNAM_MASK    = "xx????xx????xxx"
_P2_GNAM_OFF     = 0x2

# Pattern 3  (P2 GObjects + P1 GNames)
_P3_GOBJ         = _P2_GOBJ
_P3_GOBJ_MASK    = _P2_GOBJ_MASK
_P3_GOBJ_OFF     = _P2_GOBJ_OFF
_P3_GNAM         = _P1_GNAM
_P3_GNAM_MASK    = _P1_GNAM_MASK
_P3_GNAM_OFF     = _P1_GNAM_OFF

# ─────────────────────────────────────────────────────────────────────────────
# Common UE3 32-bit struct offsets (Engine.h / community RE)
# ─────────────────────────────────────────────────────────────────────────────
_OFF32 = dict(
    name_field_off = 0x2C,   # UObject.FName.dwIndex
    name_str_off   = 0x10,   # FNameEntry.Name[]
    name_encoding  = "ascii",
    is64           = False,
)

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

    # ── Section 8 / Section 8: Prejudice  (primary / default) ──────────────
    "S8": {
        "name":         "Section 8 / Prejudice",
        "process":      "S8Game-F.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x013B9B78,
        "gnames_va":    0x01377868,
        **_OFF32,
        "notes": "Section 8 + Section 8: Prejudice (S8/S9). Pattern1.",
    },

    # ── Section 9 / Prejudice (same binary family) ──────────────────────────
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

    # ── America's Army 3 ─────────────────────────────────────────────────────
    "AA3": {
        "name":         "America's Army 3",
        "process":      "AA3Game-Win32-Shipping.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "America's Army 3. Pattern1. VA must be scanned.",
    },

    # ── APB: Reloaded ────────────────────────────────────────────────────────
    "APB": {
        "name":         "APB: Reloaded",
        "process":      "APB.exe",
        "gobj_pattern": _P2_GOBJ,  "gobj_mask": _P2_GOBJ_MASK, "gobj_off": _P2_GOBJ_OFF,
        "gnam_pattern": _P2_GNAM,  "gnam_mask": _P2_GNAM_MASK, "gnam_off": _P2_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "APB: All Points Bulletin / Reloaded. Pattern2.",
    },

    # ── Blacklight: Retribution ──────────────────────────────────────────────
    "BLR": {
        "name":         "Blacklight: Retribution",
        "process":      "BLR.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Blacklight: Retribution. Pattern1.",
    },

    # ── Brink ────────────────────────────────────────────────────────────────
    "BR": {
        "name":         "Brink",
        "process":      "Brink.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Brink (Splash Damage). Pattern1.",
    },

    # ── Chivalry: Medieval Warfare ───────────────────────────────────────────
    "CC": {
        "name":         "Chivalry: Medieval Warfare",
        "process":      "UDKGame-Win32-Shipping.exe",
        "gobj_pattern": _P3_GOBJ,  "gobj_mask": _P3_GOBJ_MASK, "gobj_off": _P3_GOBJ_OFF,
        "gnam_pattern": _P3_GNAM,  "gnam_mask": _P3_GNAM_MASK, "gnam_off": _P3_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Chivalry: Medieval Warfare / Deadliest Warrior. Pattern3.",
    },

    # ── Guns of Icarus Online ────────────────────────────────────────────────
    "GA": {
        "name":         "Guns of Icarus Online",
        "process":      "UDKGame-Win32-Shipping.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Guns of Icarus Online. Pattern1.",
    },

    # ── Hawken ───────────────────────────────────────────────────────────────
    "HF": {
        "name":         "Hawken",
        "process":      "UDKGame-Win32-Shipping.exe",
        "gobj_pattern": _P2_GOBJ,  "gobj_mask": _P2_GOBJ_MASK, "gobj_off": _P2_GOBJ_OFF,
        "gnam_pattern": _P2_GNAM,  "gnam_mask": _P2_GNAM_MASK, "gnam_off": _P2_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Hawken. Pattern2.",
    },

    # ── Mass Effect 3 ────────────────────────────────────────────────────────
    "ME3": {
        "name":         "Mass Effect 3",
        "process":      "MassEffect3.exe",
        "gobj_pattern": _P2_GOBJ,  "gobj_mask": _P2_GOBJ_MASK, "gobj_off": _P2_GOBJ_OFF,
        "gnam_pattern": _P2_GNAM,  "gnam_mask": _P2_GNAM_MASK, "gnam_off": _P2_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Mass Effect 3 (UE3 base). Pattern2.",
    },

    # ── Orcs Must Die ────────────────────────────────────────────────────────
    "ODB": {
        "name":         "Orcs Must Die",
        "process":      "OrcsMustDie.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Orcs Must Die. Pattern1.",
    },

    # ── Rainbow Six Vegas 2 ──────────────────────────────────────────────────
    "R6V2": {
        "name":         "Rainbow Six: Vegas 2",
        "process":      "RainbowSixVegas2_Game.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Rainbow Six: Vegas 2. Pattern1.",
    },

    # ── Ravaged ──────────────────────────────────────────────────────────────
    "RD": {
        "name":         "Ravaged",
        "process":      "UDKGame-Win32-Shipping.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Ravaged (2012). Pattern1.",
    },

    # ── Red Orchestra 2 ─────────────────────────────────────────────────────
    "RO2": {
        "name":         "Red Orchestra 2",
        "process":      "ROGame.exe",
        "gobj_pattern": _P3_GOBJ,  "gobj_mask": _P3_GOBJ_MASK, "gobj_off": _P3_GOBJ_OFF,
        "gnam_pattern": _P3_GNAM,  "gnam_mask": _P3_GNAM_MASK, "gnam_off": _P3_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Red Orchestra 2: Heroes of Stalingrad. Pattern3.",
    },

    # ── SMNC (Super Monday Night Combat) ────────────────────────────────────
    "SMNC": {
        "name":         "Super Monday Night Combat",
        "process":      "UDKGame-Win32-Shipping.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Super Monday Night Combat. Pattern1.",
    },

    # ── Sang-Froid: Tales of Werewolves ─────────────────────────────────────
    "SOTL": {
        "name":         "Sang-Froid: Tales of Werewolves",
        "process":      "UDKGame-Win32-Shipping.exe",
        "gobj_pattern": _P2_GOBJ,  "gobj_mask": _P2_GOBJ_MASK, "gobj_off": _P2_GOBJ_OFF,
        "gnam_pattern": _P2_GNAM,  "gnam_mask": _P2_GNAM_MASK, "gnam_off": _P2_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Sang-Froid: Tales of Werewolves. Pattern2.",
    },

    # ── Sanctum ──────────────────────────────────────────────────────────────
    "ST": {
        "name":         "Sanctum",
        "process":      "UDKGame-Win32-Shipping.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Sanctum. Pattern1.",
    },

    # ── Tribes: Ascend ───────────────────────────────────────────────────────
    "TA": {
        "name":         "Tribes: Ascend",
        "process":      "TribesAscend.exe",
        "gobj_pattern": _P2_GOBJ,  "gobj_mask": _P2_GOBJ_MASK, "gobj_off": _P2_GOBJ_OFF,
        "gnam_pattern": _P2_GNAM,  "gnam_mask": _P2_GNAM_MASK, "gnam_off": _P2_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Tribes: Ascend (Hi-Rez). Pattern2.",
    },

    # ── Trine (UE3 port) ─────────────────────────────────────────────────────
    "TE": {
        "name":         "Trine",
        "process":      "Trine.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Trine. Pattern1.",
    },

    # ── Generic UDK / UE3 ────────────────────────────────────────────────────
    "UDK": {
        "name":         "Generic UDK / UE3",
        "process":      "UDKGame-Win32-Shipping.exe",
        "gobj_pattern": _P1_GOBJ,  "gobj_mask": _P1_GOBJ_MASK, "gobj_off": _P1_GOBJ_OFF,
        "gnam_pattern": _P1_GNAM,  "gnam_mask": _P1_GNAM_MASK, "gnam_off": _P1_GNAM_OFF,
        "gobjects_va":  0x0,
        "gnames_va":    0x0,
        **_OFF32,
        "notes": "Generic UDK / UE3 fallback. Try Pattern1 first.",
    },
}

# Ordered list for the UI combo-box  (S8 first as default; CUSTOM at end)
PROFILE_KEYS = ["S8"] + sorted(k for k in GAME_PROFILES if k not in ("S8", "CUSTOM")) + ["CUSTOM"]

DEFAULT_PROFILE = "S8"
