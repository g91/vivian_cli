"""Font size control — mirrors src/hooks/useFontSize.ts."""
from __future__ import annotations

def useFontSize(initial: int = 14) -> dict:
    """Manage font size."""
    size = initial
    
    def increase() -> int:
        nonlocal size
        size = min(32, size + 2)
        return size
    
    def decrease() -> int:
        nonlocal size
        size = max(8, size - 2)
        return size
    
    def set_size(s: int) -> None:
        nonlocal size
        size = max(8, min(32, s))
    
    return {
        "size": initial,
        "increase": increase,
        "decrease": decrease,
        "setSize": set_size,
    }

use_font_size = useFontSize
