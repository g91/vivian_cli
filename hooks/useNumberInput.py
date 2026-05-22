"""Number input — mirrors src/hooks/useNumberInput.ts."""
from __future__ import annotations

def useNumberInput(initialValue: int = 0, min: int = 0, max: int = 100) -> dict:
    """Manage numeric input."""
    value = initialValue
    
    def setValue(v: int) -> None:
        nonlocal value
        value = max(min, min(max, v))
    
    def increment() -> None:
        nonlocal value
        value = min(max, value + 1)
    
    def decrement() -> None:
        nonlocal value
        value = max(min, value - 1)
    
    return {
        "value": initialValue,
        "setValue": setValue,
        "increment": increment,
        "decrement": decrement,
    }

use_number_input = useNumberInput
