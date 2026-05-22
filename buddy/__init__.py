"""Buddy system — mirrors src/buddy/."""
from .types import (
    RARITIES, SPECIES, EYES, HATS, STAT_NAMES,
    RARITY_WEIGHTS, RARITY_STARS, RARITY_COLORS,
    CompanionBones, StoredCompanion, Companion,
)
from .companion import roll, roll_with_seed, get_companion, companion_user_id
from .sprites import render_sprite, render_face, sprite_frame_count
from .prompt import companion_intro_text, get_companion_intro_attachment
from .buddy_notification import is_buddy_teaser_window, is_buddy_live, find_buddy_trigger_positions
from .companion_sprite import render_companion_card, get_next_frame

__all__ = [
    "RARITIES", "SPECIES", "EYES", "HATS", "STAT_NAMES",
    "RARITY_WEIGHTS", "RARITY_STARS", "RARITY_COLORS",
    "CompanionBones", "StoredCompanion", "Companion",
    "roll", "roll_with_seed", "get_companion", "companion_user_id",
    "render_sprite", "render_face", "sprite_frame_count",
    "companion_intro_text", "get_companion_intro_attachment",
    "is_buddy_teaser_window", "is_buddy_live", "find_buddy_trigger_positions",
    "render_companion_card", "get_next_frame",
]
