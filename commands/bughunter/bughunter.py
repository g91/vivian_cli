"""bughunter command — mirrors src/commands/bughunter/.

Automated bug hunting and verification tool.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    prompt = """You are a bug hunter. Analyze the codebase for potential bugs:

1. Look for common bug patterns (null derefs, race conditions, off-by-one, etc.)
2. Check error handling paths
3. Verify edge cases are handled
4. Report findings with severity and suggested fixes

Focus on the most impactful issues first."""
    return TextResult(prompt)


bughunter = call
bughunter_cmd = call
