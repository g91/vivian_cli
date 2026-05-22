"""Pointer events — mirrors src/hooks/usePointerEvents.ts."""
from __future__ import annotations

def usePointerEvents() -> dict:
    """Handle pointer events."""
    return {"x": 0, "y": 0, "type": None}

use_pointer_events = usePointerEvents
