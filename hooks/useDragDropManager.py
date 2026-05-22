"""Drag and drop manager — mirrors src/hooks/useDragDropManager.ts."""
from __future__ import annotations
from typing import Any

def useDragDropManager() -> dict[str, Any]:
    """Manage drag and drop operations."""
    return {
        "isDragging": False,
        "draggedItem": None,
        "startDrag": lambda item: None,
        "drop": lambda: None,
    }

use_drag_drop_manager = useDragDropManager
