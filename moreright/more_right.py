"""More-right stub — mirrors src/moreright/useMoreRight.tsx.

External stub with no-op implementation; callers wire up the real plugin
if/when it's available in their environment.
"""
from __future__ import annotations

from typing import Any, Callable, Optional


class MoreRightHooks:
    """No-op hooks matching the TypeScript interface."""

    async def on_before_query(self) -> bool:
        return True

    async def on_turn_complete(self) -> None:
        pass

    def render(self) -> None:
        return None


def use_more_right(_args: Any = None) -> MoreRightHooks:
    """Return no-op more-right hooks."""
    return MoreRightHooks()
