"""Caches sub-command — mirrors src/commands/clear/caches.ts.

Clear internal caches (model list, tool registry, etc.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    """Clear internal caches."""
    from ...types.command import TextResult
    cleared: list[str] = []
    try:
        from ...api.client import _model_cache
        _model_cache.clear()
        cleared.append("model cache")
    except Exception:
        pass
    try:
        qe = getattr(context, "query_engine", None)
        if qe and hasattr(qe, "tool_cache"):
            qe.tool_cache.clear()
            cleared.append("tool cache")
    except Exception:
        pass
    msg = f"Caches cleared: {', '.join(cleared)}" if cleared else "No caches to clear."
    return TextResult(msg)
