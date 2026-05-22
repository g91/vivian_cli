"""summary command — mirrors src/commands/summary/.

Generate a summary of the current session.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    prompt = """Summarize this conversation session. Include:
1. Main topics discussed
2. Key decisions made
3. Files modified or created
4. Outstanding questions or TODOs
Keep it concise — 3-5 bullet points per section."""
    return TextResult(prompt)


showSummary = call
show_summary = call
