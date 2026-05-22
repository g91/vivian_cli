"""Command history management — mirrors src/hooks/useCommandHistory.ts."""
from __future__ import annotations
from typing import Any

def useCommandHistory(limit: int = 1000) -> dict[str, Any]:
    """Store and retrieve command history."""
    history = []
    
    def add(cmd: str) -> None:
        history.append(cmd)
        if len(history) > limit:
            history.pop(0)
    
    def get(index: int = -1) -> str | None:
        if -len(history) <= index < len(history):
            return history[index]
        return None
    
    def getAll() -> list[str]:
        return list(history)
    
    return {
        "add": add,
        "get": get,
        "getAll": getAll,
        "length": len(history),
    }

use_command_history = useCommandHistory
