"""Port of src/ink/termio/sgr.ts."""
from __future__ import annotations

from typing import Any

from .csi import csi

# SGR parameter constants
SGR_RESET = 0
SGR_BOLD = 1
SGR_DIM = 2
SGR_ITALIC = 3
SGR_UNDERLINE = 4
SGR_BLINK = 5
SGR_INVERSE = 7
SGR_HIDDEN = 8
SGR_STRIKETHROUGH = 9
SGR_BOLD_OFF = 22
SGR_ITALIC_OFF = 23
SGR_UNDERLINE_OFF = 24
SGR_INVERSE_OFF = 27
SGR_STRIKETHROUGH_OFF = 29
SGR_FG = 38
SGR_BG = 48
SGR_FG_DEFAULT = 39
SGR_BG_DEFAULT = 49

# Named ANSI colors (SGR 30-37, 90-97)
NAMED_FG = {
    "black": 30, "red": 31, "green": 32, "yellow": 33,
    "blue": 34, "magenta": 35, "cyan": 36, "white": 37,
}
NAMED_BG = {k: v + 10 for k, v in NAMED_FG.items()}
NAMED_FG_BRIGHT = {
    "black": 90, "red": 91, "green": 92, "yellow": 93,
    "blue": 94, "magenta": 95, "cyan": 96, "white": 97,
}
NAMED_BG_BRIGHT = {k: v + 10 for k, v in NAMED_FG_BRIGHT.items()}


def sgr(*codes: int) -> str:
    """Build an SGR sequence: ESC [ codes m."""
    return csi(";".join(str(c) for c in codes), "m")


def sgr_reset() -> str:
    return sgr(SGR_RESET)


def sgr_bold() -> str:
    return sgr(SGR_BOLD)


def sgr_dim() -> str:
    return sgr(SGR_DIM)


def sgr_italic() -> str:
    return sgr(SGR_ITALIC)


def sgr_underline() -> str:
    return sgr(SGR_UNDERLINE)


def sgr_inverse() -> str:
    return sgr(SGR_INVERSE)


def sgr_strikethrough() -> str:
    return sgr(SGR_STRIKETHROUGH)


def sgr_fg_named(name: str) -> str:
    code = NAMED_FG.get(name)
    if code is not None:
        return sgr(code)
    return ""


def sgr_bg_named(name: str) -> str:
    code = NAMED_BG.get(name)
    if code is not None:
        return sgr(code)
    return ""


def sgr_fg_256(n: int) -> str:
    return sgr(SGR_FG, 5, n)


def sgr_bg_256(n: int) -> str:
    return sgr(SGR_BG, 5, n)


def sgr_fg_rgb(r: int, g: int, b: int) -> str:
    return sgr(SGR_FG, 2, r, g, b)


def sgr_bg_rgb(r: int, g: int, b: int) -> str:
    return sgr(SGR_BG, 2, r, g, b)
