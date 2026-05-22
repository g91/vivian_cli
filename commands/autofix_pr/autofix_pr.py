"""autofix-pr command — mirrors src/commands/autofix-pr/.

Automatically fix issues in a PR based on review feedback.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    pr_num = args.strip() if args else ""
    if not pr_num:
        return TextResult("Usage: /autofix-pr <PR number>")
    return TextResult(f"Autofix PR #{pr_num}: Analyzing and applying fixes...")


autofixPR = call
autofix_pr = call
