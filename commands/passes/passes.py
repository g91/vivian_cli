"""passes command — mirrors src/commands/passes/passes.tsx.

Show available feature passes and subscription tier information.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    """Show available passes and features."""
    from ...types.command import TextResult
    lines = [
        "╔══════════════════════════════════╗",
        "║        Available Passes          ║",
        "╚══════════════════════════════════╝",
        "",
        "  Tier: Free",
        "  Daily requests: Unlimited (local Ollama)",
        "  Models: All installed Ollama models",
        "  Tools: Full access",
        "  Memory: Persistent across sessions",
        "",
        "Upgrade at https://vivian.d0a.net/settings",
    ]
    return TextResult("\n".join(lines))


showPasses = call
show_passes = call
