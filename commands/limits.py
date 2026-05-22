"""limits command.

Show current vivian AI rate limit and quota status.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..services.vivianAiLimits import currentLimits

if TYPE_CHECKING:
    from ..types.command import CommandContext, TextResult


def _format_limits(limits: dict) -> str:
    if not limits:
        return "No limit data yet (make a request first)"
    lines = []
    for key, value in limits.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


async def call(args: str, context: CommandContext) -> TextResult:
    del args, context
    from ..types.command import TextResult

    try:
        if currentLimits:
            return TextResult(_format_limits(currentLimits))
        return TextResult("No limit data yet (make a request first)")
    except Exception as exc:
        return TextResult(f"Limits unavailable: {exc}")
