"""Scroll position — mirrors src/hooks/useScrollPosition.ts."""
from __future__ import annotations

def useScrollPosition() -> dict:
    """Track scroll position."""
    return {"x": 0, "y": 0}

use_scroll_position = useScrollPosition
