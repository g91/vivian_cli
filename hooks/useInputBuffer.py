"""Input buffer hook — mirrors src/hooks/useInputBuffer.ts."""
from __future__ import annotations

def useInputBuffer(initialValue: str = "") -> dict:
    """Manage buffered text input."""
    state = {"buffer": initialValue}
    
    def append(text: str) -> None:
        state["buffer"] += text
    
    def clear() -> None:
        state["buffer"] = ""
    
    def get() -> str:
        return state["buffer"]
    
    return {
        'buffer': initialValue,
        'append': append,
        'clear': clear,
        'get': get,
    }

use_input_buffer = useInputBuffer
