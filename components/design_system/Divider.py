"""Divider component — mirrors src/components/design-system/Divider.tsx."""

from __future__ import annotations

from ...ink.components.TerminalSizeContext import getTerminalSizeContext
from ...ink.stringWidth import stringWidth


def Divider(
    width: int | None = None,
    color: str | None = None,
    char: str = "─",
    padding: int = 0,
    title: str | None = None,
) -> str:
    del color
    terminal_width = getTerminalSizeContext().columns
    effective_width = max(0, (width if width is not None else terminal_width) - padding)

    if title:
        title_width = stringWidth(title) + 2
        side_width = max(0, effective_width - title_width)
        left_width = side_width // 2
        right_width = side_width - left_width
        return f"{char * left_width} {title} {char * right_width}"

    return char * effective_width


__all__ = ["Divider"]