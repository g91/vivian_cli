"""diff command — mirrors src/commands/diff/diff.tsx.

Shows and explains the current git diff.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def getDiffPrompt() -> str:
    return """Analyze the git diff and explain the changes:

!`git diff HEAD`

Provide:
1. Summary of what changed
2. Files modified and why
3. Any potential issues or risks
4. Suggestions for improvement"""


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    return TextResult(getDiffPrompt())


showDiff = call
show_diff = call
get_diff_prompt = getDiffPrompt
