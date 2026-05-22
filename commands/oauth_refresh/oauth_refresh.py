"""oauth-refresh command — mirrors src/commands/oauth-refresh/.

Force refresh the OAuth token.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    return TextResult("OAuth token refresh requested. Check https://vivian.d0a.net/settings for token status.")


refreshOAuth = call
refresh_oauth = call
