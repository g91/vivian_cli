"""usage command — mirrors src/commands/usage/usage.tsx.

Shows detailed usage statistics for the current session.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def formatUsage(
    input_tokens: int = 0,
    output_tokens: int = 0,
    message_count: int = 0,
    turn_count: int = 0,
    tool_calls: int = 0,
    model: str = "",
) -> str:
    lines = [
        "╔══════════════════════════════════╗",
        "║        Usage Statistics          ║",
        "╚══════════════════════════════════╝",
        "",
        f"  Model:          {model or 'unknown'}",
        f"  Messages:       {message_count}",
        f"  Turns:          {turn_count}",
        f"  Tool calls:     {tool_calls}",
        f"  Input tokens:   {input_tokens:,}",
        f"  Output tokens:  {output_tokens:,}",
        f"  Total tokens:   {input_tokens + output_tokens:,}",
    ]
    return "\n".join(lines)


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    in_tok = out_tok = msg_count = turn_count = tool_calls = 0
    model = ""
    try:
        qe = getattr(context, "query_engine", None)
        if qe:
            in_tok = getattr(qe, "total_input_tokens", 0) or 0
            out_tok = getattr(qe, "total_output_tokens", 0) or 0
            model = getattr(qe, "model", "") or ""
            msgs = getattr(qe, "messages", []) or []
            msg_count = len(msgs)
            turn_count = sum(1 for m in msgs if getattr(m, "role", "") == "user")
            tool_calls = sum(1 for m in msgs if getattr(m, "role", "") == "tool")
    except Exception:
        pass
    return TextResult(formatUsage(in_tok, out_tok, msg_count, turn_count, tool_calls, model))


format_usage = formatUsage
