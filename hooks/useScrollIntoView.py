"""Scroll into view — mirrors src/hooks/useScrollIntoView.ts."""
from __future__ import annotations

def useScrollIntoView() -> callable:
    """Scroll element into view."""
    return lambda el, options=None: None

use_scroll_into_view = useScrollIntoView
