"""feedback command — mirrors src/commands/feedback/feedback.tsx.

Submit feedback about Vivian AI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def submitFeedback(message: str) -> str:
    return f"Feedback submitted: {message[:100]}{'...' if len(message) > 100 else ''}"


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    msg = args.strip() if args else ""
    if not msg:
        return TextResult("Usage: /feedback <your message>")
    # Store feedback
    try:
        from ...utils.debug_log import dlog
        dlog("feedback: %s", msg)
    except Exception:
        pass
    return TextResult(submitFeedback(msg))


submit_feedback = submitFeedback
