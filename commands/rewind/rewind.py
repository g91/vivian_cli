"""rewind command — mirrors src/commands/rewind/rewind.ts.

Rewinds the conversation by removing the last N assistant/user message pairs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    """Rewind conversation by N steps (default 1)."""
    from ...types.command import TextResult

    try:
        steps = int(args.strip()) if args.strip() else 1
    except ValueError:
        return TextResult(f"Invalid step count: {args}. Use a number like /rewind 2")

    steps = max(1, min(steps, 50))
    removed = 0

    try:
        qe = getattr(context, "query_engine", None)
        if qe and hasattr(qe, "messages"):
            msgs = qe.messages
            # Remove last N assistant+tool message groups
            for _ in range(steps):
                if not msgs:
                    break
                # Remove trailing tool messages
                while msgs and getattr(msgs[-1], "role", "") == "tool":
                    msgs.pop()
                    removed += 1
                # Remove assistant message
                if msgs and getattr(msgs[-1], "role", "") == "assistant":
                    msgs.pop()
                    removed += 1
                # Remove user message
                if msgs and getattr(msgs[-1], "role", "") == "user":
                    msgs.pop()
                    removed += 1
    except Exception:
        pass

    return TextResult(f"Rewound {steps} step(s). Removed {removed} messages.")


rewindConversation = call
rewind_conversation = call
