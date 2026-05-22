"""Hover state — mirrors src/hooks/useHoverState.ts."""
from __future__ import annotations

def useHoverState() -> dict:
    """Track hover state."""
    return {
        "isHovering": False,
        "ref": None,
    }

use_hover_state = useHoverState
