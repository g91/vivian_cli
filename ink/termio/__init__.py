"""Port of src/ink/termio.ts."""
from .parser import Parser
from .types import (
    defaultStyle, stylesEqual, colorsEqual, TextStyle,
    NamedColor, Color, Grapheme, TextSegment,
)

__all__ = [
    "Parser",
    "defaultStyle", "stylesEqual", "colorsEqual",
    "TextStyle", "NamedColor", "Color", "Grapheme", "TextSegment",
]
