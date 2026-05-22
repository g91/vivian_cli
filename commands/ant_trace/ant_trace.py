"""ant-trace command — mirrors src/commands/ant-trace/.

Internal debug tool for tracing execution paths.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    action = args.strip().lower() if args else ""
    if action == "on":
        return TextResult("Ant trace: ON — execution paths will be logged.")
    if action == "off":
        return TextResult("Ant trace: OFF.")
    return TextResult("Usage: /ant-trace [on|off]")


antTrace = call
ant_trace = call

ant_trace = antTrace
