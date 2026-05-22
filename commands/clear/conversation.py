"""Conversation sub-command — mirrors src/commands/clear/conversation.ts.

Clear the conversation history and start fresh.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    """Clear the conversation history."""
    from ...types.command import TextResult
    try:
        qe = getattr(context, "query_engine", None)
        if qe and hasattr(qe, "messages"):
            qe.messages.clear()
    except Exception:
        pass
    return TextResult("Conversation cleared. Starting fresh.")
