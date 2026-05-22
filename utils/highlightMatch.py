"""
Port of src/utils/highlightMatch.tsx
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING


HighlightMatchSegment = Dict[str, Any]


def highlightMatch(text, query):
    """Inverse-highlight every occurrence of `query` in `text` (case-insensitive).
Used by search dialogs to show where the query matched in result rows
and preview panes."""
    if not query:
        return text

    text_value = '' if text is None else str(text)
    query_value = str(query)
    query_lower = query_value.lower()
    text_lower = text_value.lower()

    parts: List[HighlightMatchSegment] = []
    offset = 0
    idx = text_lower.find(query_lower, offset)
    if idx == -1:
        return text_value

    while idx != -1:
        if idx > offset:
            parts.append({'text': text_value[offset:idx]})
        parts.append({'text': text_value[idx: idx + len(query_value)], 'inverse': True})
        offset = idx + len(query_value)
        idx = text_lower.find(query_lower, offset)

    if offset < len(text_value):
        parts.append({'text': text_value[offset:]})

    return parts


highlight_match = highlightMatch

