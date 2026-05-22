"""session command — mirrors src/commands/session/session.tsx.

Shows current session information: ID, message count, turn count, model, cost.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def formatSessionInfo(
    session_id: str = "",
    message_count: int = 0,
    turn_count: int = 0,
    model: str = "",
    total_cost: float = 0.0,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> str:
    """Format session information into a readable string."""
    lines = [
        "╔══════════════════════════════════╗",
        "║        Session Info              ║",
        "╚══════════════════════════════════╝",
        "",
        f"  Session ID:    {session_id}",
        f"  Model:         {model or 'unknown'}",
        f"  Messages:      {message_count}",
        f"  Turns:         {turn_count}",
        f"  Input tokens:  {input_tokens:,}",
        f"  Output tokens: {output_tokens:,}",
        f"  Total tokens:  {input_tokens + output_tokens:,}",
        f"  Est. cost:     ${total_cost:.4f}",
    ]
    return "\n".join(lines)


async def call(args: str, context: CommandContext) -> TextResult:
    """Show current session info."""
    from ...types.command import TextResult

    sid = ""
    msg_count = 0
    turn_count = 0
    model = ""
    cost = 0.0
    in_tok = 0
    out_tok = 0

    try:
        qe = getattr(context, "query_engine", None)
        if qe:
            sid = getattr(qe, "session_id", "") or ""
            msgs = getattr(qe, "messages", []) or []
            msg_count = len(msgs)
            turn_count = sum(1 for m in msgs if getattr(m, "role", "") == "user")
            model = getattr(qe, "model", "") or ""
            in_tok = getattr(qe, "total_input_tokens", 0) or 0
            out_tok = getattr(qe, "total_output_tokens", 0) or 0
    except Exception:
        pass

    try:
        ct = getattr(context, "cost_tracker", None)
        if ct:
            cost = getattr(ct, "total_cost", 0.0) or 0.0
    except Exception:
        pass

    return TextResult(formatSessionInfo(sid, msg_count, turn_count, model, cost, in_tok, out_tok))


format_session_info = formatSessionInfo
