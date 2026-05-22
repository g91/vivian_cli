"""thinkback command — mirrors src/commands/thinkback/thinkback.tsx.

Review the AI's past thinking/reasoning from earlier turns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    """Show thinking history."""
    from ...types.command import TextResult
    try:
        qe = getattr(context, "query_engine", None)
        if qe and hasattr(qe, "thinking_history"):
            history = qe.thinking_history
            if history:
                lines = ["Thinking History:", ""]
                for i, entry in enumerate(history[-10:], 1):
                    lines.append(f"  Turn {i}: {str(entry)[:120]}...")
                return TextResult("\n".join(lines))
    except Exception:
        pass
    return TextResult("No thinking history available. Enable verbose mode to capture reasoning.")


showThinkback = call
show_thinkback = call
