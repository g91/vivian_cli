"""statusline command — mirrors src/commands/statusline.tsx.

Set up the status line UI showing model, cost, and session info.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    """Configure the status line."""
    from ...types.command import TextResult
    prompt = args.strip() or "Configure my status line from my shell PS1 configuration"
    return TextResult(
        f"Create a status line configuration with the prompt: \"{prompt}\"\n\n"
        "The status line can show:\n"
        "  • Current model\n"
        "  • Session cost\n"
        "  • Token usage\n"
        "  • Git branch\n"
        "  • Active mode (plan/fast/vim)\n\n"
        "Edit ~/.vivian/settings.json to customize."
    )
