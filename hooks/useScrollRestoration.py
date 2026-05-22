"""Scroll restoration — mirrors src/hooks/useScrollRestoration.ts."""
from __future__ import annotations

def useScrollRestoration() -> dict:
    """Restore scroll position."""
    return {"saved": False, "position": 0}

use_scroll_restoration = useScrollRestoration
