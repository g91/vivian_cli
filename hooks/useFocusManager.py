"""Focus manager — mirrors src/hooks/useFocusManager.ts."""
from __future__ import annotations
from typing import Any

def useFocusManager() -> dict[str, Any]:
    """Manage UI focus state."""
    return {
        "focused": None,
        "setFocus": lambda el: None,
        "clearFocus": lambda: None,
    }

use_focus_manager = useFocusManager
