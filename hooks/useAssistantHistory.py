"""Assistant history management — mirrors src/hooks/useAssistantHistory.ts."""
from __future__ import annotations
from typing import Any

def useAssistantHistory(maxItems: int = 100) -> dict[str, Any]:
    """Manage assistant conversation history."""
    items = []
    
    def addItem(item: dict) -> None:
        items.append(item)
        if len(items) > maxItems:
            items.pop(0)
    
    def getItems() -> list[dict]:
        return list(items)
    
    def clear() -> None:
        items.clear()
    
    return {
        "items": items,
        "addItem": addItem,
        "getItems": getItems,
        "clear": clear,
        "maxItems": maxItems,
    }

use_assistant_history = useAssistantHistory
