"""thinkback-play command — mirrors src/commands/thinkback-play/.

Replay past AI thinking/reasoning step by step.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    """Replay thinking history step by step."""
    from ...types.command import TextResult
    try:
        turn = int(args.strip()) if args.strip() else 1
    except ValueError:
        return TextResult("Usage: /thinkback-play [turn_number]")

    try:
        qe = getattr(context, "query_engine", None)
        if qe and hasattr(qe, "thinking_history"):
            history = qe.thinking_history
            if 1 <= turn <= len(history):
                return TextResult(f"Turn {turn} thinking:\n{history[turn - 1]}")
            return TextResult(f"Turn {turn} not found. Available: 1-{len(history)}")
    except Exception:
        pass
    return TextResult("No thinking history to replay.")


playThinkback = call
play_thinkback = call
