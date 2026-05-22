"""stickers command — mirrors src/commands/stickers/stickers.ts."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult

STICKER_URL = "https://www.stickermule.com/viviancode"


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    from ...utils.browser import open_browser

    success = await open_browser(STICKER_URL)
    if success:
        return TextResult("Opening sticker page in browser…")
    return TextResult(f"Failed to open browser. Visit: {STICKER_URL}")


showStickers = call
show_stickers = call
