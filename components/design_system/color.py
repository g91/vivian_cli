"""Theme-aware color helper — minimal port of src/components/design-system/color.ts."""

from __future__ import annotations

from collections.abc import Callable

from ...ink.colorize import colorize
from ...utils.theme import getTheme


def color(c: str | None, theme: str, type: str = "foreground") -> Callable[[str], str]:
    def apply(text: str) -> str:
        if not c:
            return text
        if c.startswith(("rgb(", "#", "ansi256(", "ansi:")):
            return colorize(text, c, type)
        return colorize(text, str(getTheme(theme).get(c, c)), type)

    return apply


__all__ = ["color"]