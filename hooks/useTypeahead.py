"""Typeahead suggestion hook — mirrors src/hooks/useTypeahead.ts."""
from __future__ import annotations
from typing import Any

def useTypeahead(items: list[str] | None = None) -> dict[str, Any]:
    """Typeahead auto-completion."""
    item_list = items or []
    def filter_items(query: str) -> list[str]:
        if not query or not item_list:
            return []
        q = query.lower()
        return [i for i in item_list if q in i.lower()]
    
    return {
        'items': item_list,
        'filter': filter_items,
    }

use_typeahead = useTypeahead
