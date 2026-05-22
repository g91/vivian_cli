"""good-vivian command — mirrors src/commands/good-vivian/.

Positive reinforcement / encouragement for the AI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    return TextResult("Good vivian! 🎉 Keep up the great work!")


goodvivian = call
good_vivian = call
