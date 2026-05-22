"""context command — mirrors src/commands/context/context.tsx.

Shows current context: workspace dirs, model, message count, token usage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def showContext(context: CommandContext) -> str:
    lines = ["╔══════════════════════════════════╗",
             "║        Current Context           ║",
             "╚══════════════════════════════════╝", ""]
    try:
        qe = getattr(context, "query_engine", None)
        if qe:
            lines.append(f"  Model:         {getattr(qe, 'model', 'N/A')}")
            lines.append(f"  Messages:      {len(getattr(qe, 'messages', []))}")
            lines.append(f"  Input tokens:  {getattr(qe, 'total_input_tokens', 0):,}")
            lines.append(f"  Output tokens: {getattr(qe, 'total_output_tokens', 0):,}")
    except Exception:
        pass
    try:
        dirs = getattr(context, "config", {}).get("workspace_dirs", [])
        if dirs:
            lines.append(f"  Workspace dirs: {len(dirs)}")
            for d in dirs[:5]:
                lines.append(f"    • {d}")
    except Exception:
        pass
    return "\n".join(lines)


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    return TextResult(showContext(context))


show_context = showContext
