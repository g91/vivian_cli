"""insights command — mirrors src/commands/insights.ts.

Generate a session analytics report with usage patterns and insights.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    """Generate session insights report."""
    from ..types.command import TextResult

    prompt = """Analyze this conversation session and generate an insights report:

1. **Session Overview**: Duration, message count, tool usage summary
2. **Goal Analysis**: What was the user trying to accomplish?
3. **Friction Points**: Where did the user struggle or need clarification?
4. **Outcome**: Was the goal achieved? What was produced?
5. **Patterns**: Any recurring patterns in how the user works?

Format as a structured report with clear sections."""
    return TextResult(prompt)


showInsights = call
show_insights = call
