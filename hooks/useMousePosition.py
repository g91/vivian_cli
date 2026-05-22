"""Mouse position tracking — mirrors src/hooks/useMousePosition.ts."""
from __future__ import annotations

def useMousePosition() -> dict:
    """Track mouse position."""
    return {
        "x": 0,
        "y": 0,
    }

use_mouse_position = useMousePosition
