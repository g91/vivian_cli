"""Keyboard shortcuts — mirrors src/hooks/useKeyboardShortcuts.ts."""
from __future__ import annotations
from typing import Any, Callable

def useKeyboardShortcuts(bindings: dict[str, Callable] | None = None) -> dict[str, Any]:
    """Register keyboard shortcuts."""
    return {
        "bindings": bindings or {},
        "register": lambda key, fn: None,
        "unregister": lambda key: None,
    }

use_keyboard_shortcuts = useKeyboardShortcuts
