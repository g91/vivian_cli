"""Buddy notification helpers — mirrors src/buddy/useBuddyNotification.tsx.

Provides teaser/live window checks and trigger-position scanning.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Optional


def is_buddy_teaser_window() -> bool:
    """True during the April 1–7 2026 teaser window."""
    d = date.today()
    return d.year == 2026 and d.month == 4 and d.day <= 7


def is_buddy_live() -> bool:
    """True once the buddy feature is publicly live (April 2026+)."""
    d = date.today()
    return d.year > 2026 or (d.year == 2026 and d.month >= 4)


def find_buddy_trigger_positions(text: str) -> list[dict]:
    """Return character positions of '/buddy' mentions in *text*."""
    pattern = re.compile(r"/buddy\b", re.IGNORECASE)
    positions = []
    for m in pattern.finditer(text):
        positions.append({"start": m.start(), "end": m.end()})
    return positions
