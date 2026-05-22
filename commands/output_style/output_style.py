"""output-style command — mirrors src/commands/output-style/.

Deprecated output-style command.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


DEPRECATION_MESSAGE = (
    "/output-style has been deprecated. Use /config to change your output style, "
    "or set it in your settings file. Changes take effect on the next session."
)


def setOutputStyle(style: str) -> str:
    del style
    return DEPRECATION_MESSAGE


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    del args, context
    return TextResult(DEPRECATION_MESSAGE)


set_output_style = setOutputStyle
