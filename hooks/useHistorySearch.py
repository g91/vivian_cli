"""History search hook — mirrors src/hooks/useHistorySearch.ts."""
from __future__ import annotations
from typing import Any

def useHistorySearch(historyItems: list[Any] | None = None) -> dict[str, Any]:
    """Search through command/conversation history."""
    items = historyItems or []
    def search(q: str) -> list[Any]:
        return [i for i in items if q.lower() in str(i).lower()]
    return {
        'items': items,
        'filtered': [],
        'search': search,
    }

use_history_search = useHistorySearch
