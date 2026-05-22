"""session-memory command.

Show extracted session memory content.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..services.SessionMemory import getSessionMemoryContent

if TYPE_CHECKING:
    from ..types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    del args, context
    from ..types.command import TextResult

    try:
        content = await getSessionMemoryContent()
        if content:
            return TextResult(content[:2000])
        return TextResult("No session memory yet")
    except Exception as exc:
        return TextResult(f"Session memory unavailable: {exc}")
