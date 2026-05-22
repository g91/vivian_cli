"""tip command.

Show a contextual tip and record it as shown.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..services.tips import getTipToShowOnSpinner, recordShownTip

if TYPE_CHECKING:
    from ..types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    del args, context
    from ..types.command import TextResult

    try:
        tip = await getTipToShowOnSpinner()
        if not tip:
            return TextResult("No tips available")
        if isinstance(tip, dict):
            recordShownTip(tip)
            return TextResult(f"{tip.get('message', tip)}")
        return TextResult(str(tip))
    except Exception as exc:
        return TextResult(f"Tips unavailable: {exc}")
