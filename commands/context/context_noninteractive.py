"""Context noninteractive command — mirrors src/commands/context/context-noninteractive.ts."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def showContextNoninteractive(context: CommandContext | None = None) -> str:
    """Show context information in non-interactive mode."""
    lines = ["## Context Usage", ""]

    try:
        qe = getattr(context, "query_engine", None) if context is not None else None
        if qe is not None:
            model = getattr(qe, "model", None) or "N/A"
            messages = getattr(qe, "messages", None) or []
            input_tokens = getattr(qe, "total_input_tokens", 0) or 0
            output_tokens = getattr(qe, "total_output_tokens", 0) or 0

            lines.append(f"Model: {model}")
            lines.append(f"Messages: {len(messages)}")
            lines.append(f"Input tokens: {input_tokens:,}")
            lines.append(f"Output tokens: {output_tokens:,}")
    except Exception:
        pass

    try:
        config = getattr(context, "config", {}) if context is not None else {}
        workspace_dirs = config.get("workspace_dirs", []) if isinstance(config, dict) else []
        if workspace_dirs:
            lines.append(f"Workspace dirs: {len(workspace_dirs)}")
            for directory in workspace_dirs[:5]:
                lines.append(f"- {directory}")
    except Exception:
        pass

    if len(lines) == 2:
        lines.append("No context data available.")

    return "\n".join(lines)


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult

    return TextResult(showContextNoninteractive(context))


show_context_noninteractive = showContextNoninteractive
