"""Theme compatibility helpers — mirrors the exported surface of src/utils/theme.ts."""
from __future__ import annotations

import re
from typing import Any, Literal

from .systemTheme import resolveThemeSetting
from ..tui.theme import DARK_THEME, LIGHT_THEME

Theme = dict[str, Any]
ThemeName = Literal[
    "dark",
    "light",
    "light-daltonized",
    "dark-daltonized",
    "light-ansi",
    "dark-ansi",
]
ThemeSetting = Literal[
    "auto",
    "dark",
    "light",
    "light-daltonized",
    "dark-daltonized",
    "light-ansi",
    "dark-ansi",
]

THEME_NAMES: tuple[ThemeName, ...] = (
    "dark",
    "light",
    "light-daltonized",
    "dark-daltonized",
    "light-ansi",
    "dark-ansi",
)
THEME_SETTINGS: tuple[ThemeSetting, ...] = ("auto",) + THEME_NAMES


def _theme_to_dict(theme_obj: Any) -> Theme:
    return dict(vars(theme_obj))


_BASE_DARK = _theme_to_dict(DARK_THEME)
_BASE_LIGHT = _theme_to_dict(LIGHT_THEME)

_THEMES: dict[ThemeName, Theme] = {
    "dark": dict(_BASE_DARK),
    "light": dict(_BASE_LIGHT),
    "dark-daltonized": dict(_BASE_DARK),
    "light-daltonized": dict(_BASE_LIGHT),
    "dark-ansi": {
        **dict(_BASE_DARK),
        "text": "ansi:white",
        "inverseText": "ansi:black",
        "inactive": "ansi:blackBright",
        "subtle": "ansi:blackBright",
        "success": "ansi:green",
        "error": "ansi:red",
        "warning": "ansi:yellow",
        "permission": "ansi:blue",
        "suggestion": "ansi:blue",
        "vivian": "ansi:redBright",
        "diffAdded": "ansi:green",
        "diffRemoved": "ansi:red",
        "diffAddedWord": "ansi:greenBright",
        "diffRemovedWord": "ansi:redBright",
    },
    "light-ansi": {
        **dict(_BASE_LIGHT),
        "text": "ansi:black",
        "inverseText": "ansi:white",
        "inactive": "ansi:blackBright",
        "subtle": "ansi:blackBright",
        "success": "ansi:green",
        "error": "ansi:red",
        "warning": "ansi:yellow",
        "permission": "ansi:blue",
        "suggestion": "ansi:blue",
        "vivian": "ansi:redBright",
        "diffAdded": "ansi:green",
        "diffRemoved": "ansi:red",
        "diffAddedWord": "ansi:greenBright",
        "diffRemovedWord": "ansi:redBright",
    },
}

_ANSI_CODES = {
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "white": 37,
    "blackBright": 90,
    "redBright": 91,
    "greenBright": 92,
    "yellowBright": 93,
    "blueBright": 94,
    "magentaBright": 95,
    "cyanBright": 96,
    "whiteBright": 97,
}


def getTheme(themeName: ThemeName | ThemeSetting) -> Theme:
    resolved = resolveThemeSetting(themeName)
    if resolved not in _THEMES:
        resolved = "dark"
    return dict(_THEMES[resolved])


def themeColorToAnsi(themeColor: str) -> str:
    """Converts a theme color to an ANSI escape sequence for use with asciichart."""
    if not isinstance(themeColor, str):
        return "\x1b[35m"

    rgb_match = re.match(r"rgb\(\s?(\d+),\s?(\d+),\s?(\d+)\s?\)", themeColor)
    if rgb_match:
        r = int(rgb_match.group(1), 10)
        g = int(rgb_match.group(2), 10)
        b = int(rgb_match.group(3), 10)
        return f"\x1b[38;2;{r};{g};{b}m"

    if themeColor.startswith("ansi:"):
        code = _ANSI_CODES.get(themeColor[5:])
        if code is not None:
            return f"\x1b[{code}m"

    return "\x1b[35m"


theme_color_to_ansi = themeColorToAnsi
get_theme = getTheme

