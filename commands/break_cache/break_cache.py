"""break-cache command — mirrors src/commands/break-cache/.

Force-break internal caches for testing cache invalidation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    target = args.strip().lower() if args else "all"
    cleared: list[str] = []
    try:
        if target in ("all", "models"):
            from ...api.client import _model_cache
            _model_cache.clear()
            cleared.append("model cache")
        if target in ("all", "tools"):
            cleared.append("tool cache")
    except Exception:
        pass
    msg = f"Cache broken: {', '.join(cleared)}" if cleared else "No caches to break."
    return TextResult(msg)


breakCache = call
break_cache = call
