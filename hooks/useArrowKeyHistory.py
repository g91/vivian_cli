"""Arrow key history navigation — mirrors src/hooks/useArrowKeyHistory.ts."""
from __future__ import annotations

def useArrowKeyHistory(history: list[str] | None = None) -> dict:
    """Navigate command history with arrow keys."""
    idx = 0
    items = history or []
    
    def goUp() -> str:
        nonlocal idx
        idx = max(0, idx - 1)
        return items[idx] if idx < len(items) else ""
    
    def goDown() -> str:
        nonlocal idx
        idx = min(len(items) - 1, idx + 1)
        return items[idx] if idx < len(items) else ""
    
    return {"goUp": goUp, "goDown": goDown, "currentIndex": idx}

use_arrow_key_history = useArrowKeyHistory
