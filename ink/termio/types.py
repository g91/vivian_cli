"""Port of src/ink/termio/types.ts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

NamedColor = Literal[
    "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
    "brightBlack", "brightRed", "brightGreen", "brightYellow",
    "brightBlue", "brightMagenta", "brightCyan", "brightWhite",
]

Color = (
    dict[str, Any]  # {type: 'named', name: NamedColor}
    | dict[str, Any]  # {type: 'indexed', index: int}
    | dict[str, Any]  # {type: 'rgb', r: int, g: int, b: int}
)

UnderlineStyle = Literal["single", "double", "curly"]

@dataclass
class TextStyle:
    fg: Color | None = None
    bg: Color | None = None
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: UnderlineStyle | None = None
    strikethrough: bool = False
    inverse: bool = False
    blink: bool = False
    hidden: bool = False

    def copy(self) -> TextStyle:
        return TextStyle(
            fg=self.fg, bg=self.bg, bold=self.bold, dim=self.dim,
            italic=self.italic, underline=self.underline,
            strikethrough=self.strikethrough, inverse=self.inverse,
            blink=self.blink, hidden=self.hidden,
        )


defaultStyle = TextStyle()


def colorsEqual(a: Color | None, b: Color | None) -> bool:
    if a is b:
        return True
    if a is None or b is None:
        return False
    return a == b


def stylesEqual(a: TextStyle, b: TextStyle) -> bool:
    return (
        colorsEqual(a.fg, b.fg)
        and colorsEqual(a.bg, b.bg)
        and a.bold == b.bold
        and a.dim == b.dim
        and a.italic == b.italic
        and a.underline == b.underline
        and a.strikethrough == b.strikethrough
        and a.inverse == b.inverse
        and a.blink == b.blink
        and a.hidden == b.hidden
    )


@dataclass
class Grapheme:
    text: str
    width: int = 1


@dataclass
class TextSegment:
    graphemes: list[Grapheme] = field(default_factory=list)
    style: TextStyle = field(default_factory=TextStyle)


CursorDirection = Literal["up", "down", "left", "right", "home", "end"]

CursorAction = dict[str, Any]
EraseAction = dict[str, Any]
ScrollAction = dict[str, Any]
ModeAction = dict[str, Any]
LinkAction = dict[str, Any]
TitleAction = dict[str, Any]
Action = dict[str, Any]


colors_equal = colorsEqual
styles_equal = stylesEqual
