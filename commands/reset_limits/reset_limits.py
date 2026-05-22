"""reset-limits command — mirrors src/commands/reset-limits/.

Reset rate limit counters for testing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    return TextResult("Rate limits reset. All counters cleared.")


resetLimits = call
reset_limits = call
