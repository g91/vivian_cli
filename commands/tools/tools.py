"""tools command — mirrors src/commands/tools/tools.tsx.

List all available tools that the AI can use.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def formatTools(tools: list) -> str:
    if not tools:
        return "No tools available."
    lines = ["Available Tools:", ""]
    for t in tools:
        if isinstance(t, str):
            name = t
            desc = ""
        elif isinstance(t, dict):
            name = t.get("name", "")
            desc = t.get("description", "")
        else:
            name = getattr(t, "name", "")
            desc = getattr(t, "description", "")
        lines.append(f"  • {name}: {desc}")
    return "\n".join(lines)


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult

    tools = None
    try:
        tools = getattr(context, "tools", None)

        if tools is None:
            options = getattr(context, "options", None)
            tools = getattr(options, "tools", None)

        if tools is None and isinstance(context, dict):
            tools = context.get("tools")
            if tools is None:
                options = context.get("options")
                if isinstance(options, dict):
                    tools = options.get("tools")

        if tools is None:
            qe = getattr(context, "query_engine", None)
            tools = getattr(qe, "tools", None) if qe else None
    except Exception:
        tools = None

    if tools:
        return TextResult(formatTools(list(tools)))
    return TextResult("Tool registry not available.")


format_tools = formatTools
