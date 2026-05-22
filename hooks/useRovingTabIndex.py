"""Roving tab index — mirrors src/hooks/useRovingTabIndex.ts."""
from __future__ import annotations
from typing import Any

def useRovingTabIndex(items: list[Any] | None = None) -> dict[str, Any]:
    """Manage roving tab index for accessibility."""
    current = 0
    item_list = items or []
    
    def setFocus(index: int) -> None:
        nonlocal current
        current = max(0, min(index, len(item_list) - 1))
    
    return {"current": current, "setFocus": setFocus}

use_roving_tab_index = useRovingTabIndex
