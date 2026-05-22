"""version command — mirrors src/commands/version.ts.

Prints the current Vivian CLI version.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types.command import CommandContext, TextResult

from ..constants import PRODUCT_NAME, PRODUCT_VERSION


def getVersionString() -> str:
    """Get the version string."""
    return f"{PRODUCT_NAME} v{PRODUCT_VERSION}"


async def call(args: str, context: CommandContext) -> TextResult:
    """Print version."""
    from ..types.command import TextResult
    return TextResult(getVersionString())


get_version_string = getVersionString
