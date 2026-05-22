"""Cursor tracking — mirrors src/hooks/useCursorTracking.ts."""
from __future__ import annotations

def useCursorTracking() -> dict:
    """Track cursor position."""
    return {
        "x": 0,
        "y": 0,
        "active": False,
    }

use_cursor_tracking = useCursorTracking
