"""privacy-settings command — mirrors src/commands/privacy-settings/.

Manage privacy and data collection settings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


FALLBACK_MESSAGE = "Review and manage your privacy settings at https://api-vivian.d0a.net/settings/data-privacy-controls"


def showPrivacySettings(config: dict | None = None) -> str:
    """Show privacy settings fallback message."""
    _ = config
    return FALLBACK_MESSAGE


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    _ = args, context
    return TextResult(FALLBACK_MESSAGE)


show_privacy_settings = showPrivacySettings
