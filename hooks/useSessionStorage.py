"""Session storage — mirrors src/hooks/useSessionStorage.ts."""
from __future__ import annotations
from typing import Any

def useSessionStorage(key: str, initialValue: Any = None) -> tuple[Any, callable]:
    """Use session storage."""
    value = initialValue
    
    def setValue(v: Any) -> None:
        nonlocal value
        value = v
    
    return (value, setValue)

use_session_storage = useSessionStorage
