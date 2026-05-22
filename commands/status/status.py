"""status command — mirrors src/commands/status/status.tsx.

Shows system status: API connection, model, session info, memory usage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def formatStatus(info: dict) -> str:
    lines = ["╔══════════════════════════════════╗",
             "║        System Status             ║",
             "╚══════════════════════════════════╝", ""]
    for key, value in info.items():
        lines.append(f"  {key}: {value}")
    return "\n".join(lines)


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    import sys, os

    info = {
        "Python": sys.version.split()[0],
        "PID": os.getpid(),
        "API": "checking...",
        "Model": "unknown",
        "Messages": "0",
    }
    client = getattr(context, "client", None)
    try:
        qe = getattr(context, "query_engine", None)
        if qe:
            info["Model"] = getattr(qe, "model", "unknown")
            info["Messages"] = str(len(getattr(qe, "messages", [])))
            if client is None:
                client = getattr(qe, "client", None)
    except Exception:
        pass
    try:
        if client is not None and hasattr(client, "health"):
            health = await client.health()
            if isinstance(health, dict):
                info["API"] = str(health.get("status", "unknown"))
            else:
                info["API"] = str(health)
        else:
            info["API"] = "unavailable"
    except Exception:
        info["API"] = "unreachable"
    return TextResult(formatStatus(info))


format_status = formatStatus
