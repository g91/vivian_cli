"""Companion logic — mirrors src/buddy/companion.ts.

Deterministic companion generation using a seeded PRNG (Mulberry32 equivalent).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .types import (
    EYES, HATS, RARITIES, RARITY_WEIGHTS, SPECIES, STAT_NAMES,
    Companion, CompanionBones, StoredCompanion,
)

SALT = "friend-2026-401"


def _mulberry32(seed: int):
    """Mulberry32 seeded PRNG — matches the TypeScript implementation."""
    a = seed & 0xFFFFFFFF

    def _next() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * (61 | t))) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0

    return _next


def _hash_string(s: str) -> int:
    """FNV-1a 32-bit hash — matches the fallback branch in companion.ts."""
    h = 2166136261
    for ch in s.encode("utf-8"):
        h ^= ch
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def _pick(rng, seq):
    return seq[int(rng() * len(seq))]


def _roll_rarity(rng) -> str:
    total = sum(RARITY_WEIGHTS.values())
    roll = rng() * total
    for rarity in RARITIES:
        roll -= RARITY_WEIGHTS[rarity]
        if roll < 0:
            return rarity
    return "common"


_RARITY_FLOOR: dict[str, int] = {
    "common": 5,
    "uncommon": 15,
    "rare": 25,
    "epic": 35,
    "legendary": 50,
}


def _roll_stats(rng, rarity: str) -> dict[str, int]:
    floor = _RARITY_FLOOR[rarity]
    peak = _pick(rng, STAT_NAMES)
    dump = peak
    while dump == peak:
        dump = _pick(rng, STAT_NAMES)
    stats: dict[str, int] = {}
    for name in STAT_NAMES:
        if name == peak:
            stats[name] = min(100, floor + 50 + int(rng() * 30))
        elif name == dump:
            stats[name] = max(1, floor - 10 + int(rng() * 15))
        else:
            stats[name] = floor + int(rng() * 40)
    return stats


class Roll:
    def __init__(self, bones: CompanionBones, inspiration_seed: int) -> None:
        self.bones = bones
        self.inspiration_seed = inspiration_seed


def _roll_from(rng) -> Roll:
    rarity = _roll_rarity(rng)
    bones = CompanionBones(
        rarity=rarity,
        species=_pick(rng, SPECIES),
        eye=_pick(rng, EYES),
        hat="none" if rarity == "common" else _pick(rng, HATS),
        shiny=rng() < 0.01,
        stats=_roll_stats(rng, rarity),
    )
    inspiration_seed = int(rng() * 1e9)
    return Roll(bones, inspiration_seed)


_roll_cache: Optional[dict] = None


def roll(user_id: str) -> Roll:
    """Deterministic roll for *user_id*.  Cached per process."""
    global _roll_cache
    key = user_id + SALT
    if _roll_cache and _roll_cache.get("key") == key:
        return _roll_cache["value"]
    value = _roll_from(_mulberry32(_hash_string(key)))
    _roll_cache = {"key": key, "value": value}
    return value


def roll_with_seed(seed: str) -> Roll:
    return _roll_from(_mulberry32(_hash_string(seed)))


def companion_user_id() -> str:
    try:
        cfg_path = Path.home() / ".vivian" / "config.json"
        cfg = json.loads(cfg_path.read_text())
        return (
            cfg.get("oauthAccount", {}).get("accountUuid")
            or cfg.get("userID")
            or "anon"
        )
    except Exception:
        return "anon"


def get_companion() -> Optional[Companion]:
    """Load stored companion soul + regenerate bones from user_id."""
    try:
        cfg_path = Path.home() / ".vivian" / "config.json"
        cfg = json.loads(cfg_path.read_text())
        stored_data = cfg.get("companion")
        if not stored_data:
            return None
        stored = StoredCompanion.from_dict(stored_data)
        r = roll(companion_user_id())
        b = r.bones
        return Companion(
            rarity=b.rarity,
            species=b.species,
            eye=b.eye,
            hat=b.hat,
            shiny=b.shiny,
            stats=b.stats,
            name=stored.name,
            personality=stored.personality,
            hatched_at=stored.hatched_at,
        )
    except Exception:
        return None
