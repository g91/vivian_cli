"""Navigation history — mirrors src/hooks/useNavigationHistory.ts."""
from __future__ import annotations
from typing import Any

def useNavigationHistory() -> dict[str, Any]:
    """Manage navigation history."""
    history = []
    current = 0
    
    def push(item: Any) -> None:
        nonlocal current
        history.append(item)
        current = len(history) - 1
    
    def back() -> Any:
        nonlocal current
        if current > 0:
            current -= 1
        return history[current] if history else None
    
    def forward() -> Any:
        nonlocal current
        if current < len(history) - 1:
            current += 1
        return history[current] if history else None
    
    return {
        "history": history,
        "push": push,
        "back": back,
        "forward": forward,
    }

use_navigation_history = useNavigationHistory
