"""Companion sprite renderer for the TUI — mirrors src/buddy/CompanionSprite.tsx.

Renders the companion as ASCII art with optional animation cycling.
"""
from __future__ import annotations

import time
from typing import Optional

from .companion import get_companion
from .sprites import render_sprite, sprite_frame_count
from .types import RARITY_COLORS, RARITY_STARS, CompanionBones


def render_companion_card(frame: int = 0) -> Optional[str]:
    """Render the companion as a text card.  Returns None if no companion hatched."""
    companion = get_companion()
    if not companion:
        return None

    lines = render_sprite(companion, frame)
    sprite_str = "\n".join(lines)
    stars = RARITY_STARS.get(companion.rarity, "")
    shiny = " ✨" if companion.shiny else ""

    stats_lines = "  ".join(
        f"{k[:3]}:{v}" for k, v in companion.stats.items()
    )

    return (
        f"╭── {companion.name} ──╮\n"
        f"{sprite_str}\n"
        f"╰{'─' * (len(companion.name) + 6)}╯\n"
        f"{stars}{shiny}  {companion.species}\n"
        f"{stats_lines}"
    )


def get_next_frame(species: str, current_frame: int) -> int:
    """Advance the animation frame for *species*."""
    return (current_frame + 1) % sprite_frame_count(species)
