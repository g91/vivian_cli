"""backfill-sessions command — mirrors src/commands/backfill-sessions/.

Backfill missing session data from remote hosts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    return TextResult("Backfill sessions: Scanning for missing session data...")


backfillSessions = call
backfill_sessions = call

backfill_sessions = backfillSessions
