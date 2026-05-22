"""Theme-aware text helpers — minimal port of src/components/design-system/ThemedText.tsx."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any, Iterator

from ...utils.theme import Theme, getTheme
from .ThemeProvider import useTheme


_TEXT_HOVER_COLOR: ContextVar[str | None] = ContextVar("text_hover_color", default=None)


def resolveColor(color: str | None, theme: Theme) -> str | None:
    if not color:
        return None
    if color.startswith(("rgb(", "#", "ansi256(", "ansi:")):
        return color
    return str(theme.get(color, color))


@contextmanager
def TextHoverColorContext(color: str | None) -> Iterator[None]:
    token: Token[str | None] = _TEXT_HOVER_COLOR.set(color)
    try:
        yield None
    finally:
        _TEXT_HOVER_COLOR.reset(token)


@dataclass(slots=True)
class ThemedText:
    children: Any = None
    color: str | None = None
    backgroundColor: str | None = None
    dimColor: bool = False
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
    inverse: bool = False
    wrap: str = "wrap"

    def render(self) -> str:
        theme_name = useTheme()[0]
        theme = getTheme(theme_name)
        hover_color = _TEXT_HOVER_COLOR.get()
        resolved_color = resolveColor(self.color or hover_color, theme)
        if self.color is None and hover_color is None and self.dimColor:
            resolved_color = str(theme.get("inactive", ""))
        resolved_background = resolveColor(self.backgroundColor, theme)
        text = "" if self.children is None else str(self.children)
        prefixes: list[str] = []
        if resolved_color:
            prefixes.append(f"color={resolved_color}")
        if resolved_background:
            prefixes.append(f"bg={resolved_background}")
        if self.bold:
            prefixes.append("bold")
        if self.italic:
            prefixes.append("italic")
        if self.underline:
            prefixes.append("underline")
        if self.strikethrough:
            prefixes.append("strikethrough")
        if self.inverse:
            prefixes.append("inverse")
        if not prefixes:
            return text
        return f"<{', '.join(prefixes)}>{text}</>"

    def __str__(self) -> str:
        return self.render()


__all__ = ["TextHoverColorContext", "ThemedText", "resolveColor"]