"""btw command — mirrors src/commands/btw/btw.tsx.

Send a "by the way" message — injects a user message into the conversation
without resetting the turn, useful for mid-conversation corrections.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    """Send a 'by the way' message."""
    from ...types.command import TextResult
    msg = args.strip() if args else ""
    if not msg:
        return TextResult("Usage: /btw <message> — injects a message into the conversation")
    try:
        qe = getattr(context, "query_engine", None)
        if qe and hasattr(qe, "messages"):
            from ...api.client import Message
            qe.messages.append(Message(role="user", content=f"[BTW] {msg}"))
    except Exception:
        pass
    return TextResult(f"BTW: {msg}")


btwMessage = call
btw_message = call
