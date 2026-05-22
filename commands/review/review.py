"""review command (sub-module) — mirrors src/commands/review/.

Ultrareview and remote review functionality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    """Run ultrareview or manage review sessions."""
    from ...types.command import TextResult
    parts = args.strip().split(maxsplit=1) if args.strip() else []
    action = parts[0].lower() if parts else ""

    if action == "ultra":
        return TextResult("Ultrareview: Deep analysis mode. This may take 10-20 minutes.")

    if action == "status":
        return TextResult("Review: No active review sessions.")

    return TextResult("Usage: /review [ultra|status]")


reviewChanges = call
review_changes = call
