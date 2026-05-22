"""Message predicate helpers — mirrors src/utils/messagePredicates.ts"""
from __future__ import annotations

from typing import Any


def is_human_turn(m: dict[str, Any]) -> bool:
    """Return True if the message is a regular (non-meta, non-tool) user message."""
    return (
        m.get("type") == "user"
        and not m.get("isMeta", False)
        and not m.get("is_meta", False)
        and m.get("toolUseResult") is None
        and m.get("tool_use_result") is None
    )
