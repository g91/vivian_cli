"""debug-tool-call command — mirrors src/commands/debug-tool-call/.

Debug individual tool calls with verbose logging.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    action = args.strip().lower() if args else ""
    if action == "on":
        return TextResult("Debug tool calls: ON — all tool calls will be logged verbosely.")
    if action == "off":
        return TextResult("Debug tool calls: OFF.")
    return TextResult("Usage: /debug-tool-call [on|off]")


debugToolCall = call
debug_tool_call = call
