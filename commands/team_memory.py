"""team-memory command.

Show whether team memory sync is available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..services.teamMemorySync import isTeamMemorySyncAvailable

if TYPE_CHECKING:
    from ..types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    del args, context
    from ..types.command import TextResult

    return TextResult(f"Team memory sync: {'available' if isTeamMemorySyncAvailable() else 'not available'}")
