"""Global shortcuts — mirrors src/hooks/useGlobalShortcuts.ts."""
from __future__ import annotations
from typing import Any

def useGlobalShortcuts(shortcuts: dict[str, Any] | None = None) -> dict[str, Any]:
    """Register global keyboard shortcuts."""
    return {
        "shortcuts": shortcuts or {},
        "register": lambda key, handler: None,
        "unregister": lambda key: None,
    }

use_global_shortcuts = useGlobalShortcuts
