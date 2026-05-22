"""issue command — mirrors src/commands/issue/issue.tsx.

Create a GitHub issue from the current conversation context.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    title = args.strip() if args else ""
    if not title:
        return TextResult("Usage: /issue <title> — creates a GitHub issue from context")
    prompt = f"""Create a GitHub issue with the following:

Title: {title}

Based on the conversation context, write:
1. A clear description of the issue
2. Steps to reproduce (if applicable)
3. Expected vs actual behavior
4. Any relevant context or screenshots

Use `gh issue create` to create the issue."""
    return TextResult(prompt)


createIssue = call
create_issue = call
