"""onboarding command — mirrors src/commands/onboarding/onboarding.tsx.

Run the onboarding flow for new users.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    lines = [
        "Welcome to Vivian AI! 🚀",
        "",
        "Quick start:",
        "  1. Type any message to chat with Vivian",
        "  2. Use /model to see available models",
        "  3. Use /help to see all commands",
        "  4. Use /init to create a vivian.md for your project",
        "  5. Use /memory to see what Vivian remembers",
        "",
        "Vivian can:",
        "  • Read and edit files",
        "  • Run shell commands",
        "  • Search the web",
        "  • Manage git repos",
        "  • Remember context across sessions",
        "",
        "Happy coding! 🎉",
    ]
    return TextResult("\n".join(lines))


startOnboarding = call
start_onboarding = call
