"""stats command — mirrors src/commands/stats/stats.tsx.

Shows session statistics: message counts, token usage, tool calls, timing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def formatStats(info: dict) -> str:
    lines = ["╔══════════════════════════════════╗",
             "║        Session Stats             ║",
             "╚══════════════════════════════════╝", ""]
    for key, value in info.items():
        lines.append(f"  {key}: {value}")
    return "\n".join(lines)


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    info: dict[str, str] = {}
    try:
        qe = getattr(context, "query_engine", None)
        if qe:
            msgs = getattr(qe, "messages", []) or []
            info["Total messages"] = str(len(msgs))
            info["User messages"] = str(sum(1 for m in msgs if getattr(m, "role", "") == "user"))
            info["Assistant messages"] = str(sum(1 for m in msgs if getattr(m, "role", "") == "assistant"))
            info["Tool calls"] = str(sum(1 for m in msgs if getattr(m, "role", "") == "tool"))
            info["Input tokens"] = f"{getattr(qe, 'total_input_tokens', 0):,}"
            info["Output tokens"] = f"{getattr(qe, 'total_output_tokens', 0):,}"
    except Exception:
        pass
    return TextResult(formatStats(info))


format_stats = formatStats
