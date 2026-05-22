"""extra-usage command — mirrors src/commands/extra-usage/.

Shows extra usage details including per-model breakdown.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def showExtraUsage(context: CommandContext | None = None) -> str:
    """Show extra usage details."""
    lines = ["Extra Usage Details:", ""]
    try:
        if context:
            qe = getattr(context, "query_engine", None)
            if qe:
                lines.append(f"  Session ID: {getattr(qe, 'session_id', 'N/A')}")
                lines.append(f"  Total requests: {getattr(qe, 'request_count', 0)}")
    except Exception:
        pass
    lines.append("  Per-model breakdown not yet available.")
    return "\n".join(lines)


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    return TextResult(showExtraUsage(context))


show_extra_usage = showExtraUsage
