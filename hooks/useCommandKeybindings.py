"""Command keybindings hook — mirrors src/hooks/useCommandKeybindings.ts."""
from __future__ import annotations
from typing import Any

def useCommandKeybindings(handlers: dict[str, Any] | None = None) -> dict[str, Any]:
    """Register command keybindings."""
    return {'handlers': handlers or {}, 'active': True}

use_command_keybindings = useCommandKeybindings
