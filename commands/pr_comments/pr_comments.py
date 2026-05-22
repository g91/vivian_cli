"""pr_comments command — mirrors src/commands/pr_comments/.

Review PR comments and suggest responses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    pr_num = args.strip() if args else ""
    prompt = f"""Review the PR comments{' for PR #' + pr_num if pr_num else ''}:

1. Run `gh pr view {pr_num or ''} --comments` to get comments
2. Analyze each comment thread
3. Suggest responses or code changes for unresolved threads
4. Highlight any blocking issues

Be concise and actionable."""
    return TextResult(prompt)


showPRComments = call
show_pr_comments = call
