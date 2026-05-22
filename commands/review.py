"""review command — mirrors src/commands/review.ts.

Reviews a pull request with thorough code analysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types.command import CommandContext, TextResult


def getReviewPrompt(pr_number: str = "") -> str:
    """Build the review prompt."""
    return f"""You are an expert code reviewer. Follow these steps:

1. If no PR number is provided, run `gh pr list` to show open PRs
2. If a PR number is provided, run `gh pr view <number>` to get PR details
3. Run `gh pr diff <number>` to get the diff
4. Analyze the changes and provide a thorough code review that includes:
   - Overview of what the PR does
   - Analysis of code quality and style
   - Specific suggestions for improvements
   - Any potential issues or risks

Keep your review concise but thorough. Focus on:
- Code correctness
- Following project conventions
- Performance implications
- Test coverage
- Security considerations

Format your review with clear sections and bullet points.

PR number: {pr_number}"""


async def call(args: str, context: CommandContext) -> TextResult:
    """Review a pull request."""
    from ..types.command import TextResult
    return TextResult(getReviewPrompt(args.strip()))


reviewCode = call
review_code = call
get_review_prompt = getReviewPrompt
