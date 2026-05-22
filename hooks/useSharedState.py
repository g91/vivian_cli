"""Shared state — mirrors src/hooks/useSharedState.ts."""
from __future__ import annotations
from typing import Any

shared_state = {}

def useSharedState(key: str, initialValue: Any = None) -> tuple[Any, callable]:
    """Shared state across components."""
    if key not in shared_state:
        shared_state[key] = initialValue
    
    def setState(v: Any) -> None:
        shared_state[key] = v
    
    return (shared_state[key], setState)

use_shared_state = useSharedState
