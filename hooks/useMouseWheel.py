"""Mouse wheel — mirrors src/hooks/useMouseWheel.ts."""
from __future__ import annotations

def useMouseWheel(onScroll: callable = None) -> dict:
    """Handle mouse wheel scrolling."""
    return {"onScroll": onScroll}

use_mouse_wheel = useMouseWheel
