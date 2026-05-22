"""Nested state management — mirrors src/hooks/useNestedState.ts."""
from __future__ import annotations
from typing import Any

def useNestedState(initialState: dict[str, Any]) -> dict[str, Any]:
    """Manage deeply nested state."""
    state = dict(initialState)
    
    def setState(path: str, value: Any) -> None:
        keys = path.split('.')
        current = state
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
    
    def getState(path: str) -> Any:
        keys = path.split('.')
        current = state
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None
        return current
    
    return {
        "state": state,
        "setState": setState,
        "getState": getState,
    }

use_nested_state = useNestedState
