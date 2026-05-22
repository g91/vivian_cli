"""Virtual scroll hook — mirrors src/hooks/useVirtualScroll.ts."""
from __future__ import annotations
from typing import Any

def useVirtualScroll(
    totalItems: int,
    itemHeight: int,
    containerHeight: int,
) -> dict[str, Any]:
    """Manage virtual scrolling for large lists."""
    state = {
        'visibleStart': 0,
        'visibleEnd': min(totalItems, containerHeight // max(itemHeight, 1)),
    }
    
    def scroll(offset: int) -> None:
        state['visibleStart'] = max(0, offset // max(itemHeight, 1))
        state['visibleEnd'] = min(totalItems, state['visibleStart'] + containerHeight // max(itemHeight, 1))
    
    return {
        'visibleStart': state['visibleStart'],
        'visibleEnd': state['visibleEnd'],
        'scroll': scroll,
    }

use_virtual_scroll = useVirtualScroll
