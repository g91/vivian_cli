"""Context menu — mirrors src/hooks/useContextMenu.ts."""
from __future__ import annotations
from typing import Any

def useContextMenu(items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Display context menu."""
    return {
        "items": items or [],
        "show": lambda x, y: None,
        "hide": lambda: None,
    }

use_context_menu = useContextMenu
