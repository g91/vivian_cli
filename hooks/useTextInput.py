"""Text input hook — mirrors src/hooks/useTextInput.ts."""
from __future__ import annotations
from typing import Any, Callable

def useTextInput(
    initialValue: str = "",
    onChange: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Manage text input state."""
    state = {"value": initialValue}
    
    def setValue(val: str) -> None:
        state["value"] = val
        if onChange:
            onChange(val)
    
    return {
        'value': initialValue,
        'setValue': setValue,
        'onChange': onChange,
    }

use_text_input = useTextInput
