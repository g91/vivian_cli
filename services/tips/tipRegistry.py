"""Tip registry — mirrors src/services/tips/tipRegistry.ts."""
from __future__ import annotations

from typing import Optional

Tip = dict  # {id, cooldownSessions, condition?, text}
TipContext = dict

# Registry of all tips
_tip_registry: list[Tip] = []


def registerTip(tip: Tip) -> None:
    """Register a tip in the registry."""
    _tip_registry.append(tip)


async def getRelevantTips(context: Optional[TipContext] = None) -> list[Tip]:
    """Get all tips relevant in the current context.

    Mirrors getRelevantTips() from tipRegistry.ts.
    """
    from .tipHistory import getSessionsSinceLastShown
    relevant: list[Tip] = []
    for tip in _tip_registry:
        cooldown = tip.get("cooldownSessions", 0)
        sessions_since = getSessionsSinceLastShown(tip["id"])
        if sessions_since < cooldown:
            continue
        condition = tip.get("condition")
        if condition is not None:
            try:
                result = condition(context or {})
                if hasattr(result, "__await__"):
                    result = await result
                if not result:
                    continue
            except Exception:
                continue
        relevant.append(tip)
    return relevant


get_relevant_tips = getRelevantTips
register_tip = registerTip
