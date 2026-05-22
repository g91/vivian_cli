"""Port of src/ink/colorize.ts."""
from __future__ import annotations

import re
from typing import Any

from .styles import Color, TextStyles

RGB_REGEX = re.compile(r"^rgb\(\s?(\d+),\s?(\d+),\s?(\d+)\s?\)$")
ANSI_REGEX = re.compile(r"^ansi256\(\s?(\d+)\s?\)$")

_NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "red": (205, 0, 0),
    "green": (0, 205, 0),
    "yellow": (205, 205, 0),
    "blue": (0, 0, 238),
    "magenta": (205, 0, 205),
    "cyan": (0, 205, 205),
    "white": (229, 229, 229),
    "blackBright": (127, 127, 127),
    "redBright": (255, 0, 0),
    "greenBright": (0, 255, 0),
    "yellowBright": (255, 255, 0),
    "blueBright": (92, 92, 255),
    "magentaBright": (255, 0, 255),
    "cyanBright": (0, 255, 255),
    "whiteBright": (255, 255, 255),
}

_ANSI_256_PALETTE: dict[int, tuple[int, int, int]] = {}
# Build 6x6x6 color cube
for _r in range(6):
    for _g in range(6):
        for _b in range(6):
            idx = 16 + 36 * _r + 6 * _g + _b
            _ANSI_256_PALETTE[idx] = (
                0 if _r == 0 else 55 + _r * 40,
                0 if _g == 0 else 55 + _g * 40,
                0 if _b == 0 else 55 + _b * 40,
            )
# Grayscale
for _i in range(24):
    v = 8 + _i * 10
    _ANSI_256_PALETTE[232 + _i] = (v, v, v)


def _color_to_sgr_params(color: str) -> str:
    """Convert a color string to SGR parameters."""
    if color.startswith("ansi:"):
        name = color[5:]
        named_map = {
            "black": "30", "red": "31", "green": "32", "yellow": "33",
            "blue": "34", "magenta": "35", "cyan": "36", "white": "37",
            "blackBright": "90", "redBright": "91", "greenBright": "92",
            "yellowBright": "93", "blueBright": "94", "magentaBright": "95",
            "cyanBright": "96", "whiteBright": "97",
        }
        return named_map.get(name, "39")
    if color.startswith("#"):
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        return f"38;2;{r};{g};{b}"
    m = ANSI_REGEX.match(color)
    if m:
        return f"38;5;{int(m.group(1))}"
    m = RGB_REGEX.match(color)
    if m:
        return f"38;2;{m.group(1)};{m.group(2)};{m.group(3)}"
    return "39"


def _color_to_bg_sgr_params(color: str) -> str:
    """Convert a color string to background SGR parameters."""
    if color.startswith("ansi:"):
        name = color[5:]
        named_map = {
            "black": "40", "red": "41", "green": "42", "yellow": "43",
            "blue": "44", "magenta": "45", "cyan": "46", "white": "47",
            "blackBright": "100", "redBright": "101", "greenBright": "102",
            "yellowBright": "103", "blueBright": "104", "magentaBright": "105",
            "cyanBright": "106", "whiteBright": "107",
        }
        return named_map.get(name, "49")
    if color.startswith("#"):
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        return f"48;2;{r};{g};{b}"
    m = ANSI_REGEX.match(color)
    if m:
        return f"48;5;{int(m.group(1))}"
    m = RGB_REGEX.match(color)
    if m:
        return f"48;2;{m.group(1)};{m.group(2)};{m.group(3)}"
    return "49"


def colorize(text: str, color: str | None, type: str) -> str:
    if not color:
        return text
    if type == "foreground":
        params = _color_to_sgr_params(color)
    else:
        params = _color_to_bg_sgr_params(color)
    return f"\x1b[{params}m{text}\x1b[0m"


def applyTextStyles(text: str, styles: TextStyles) -> str:
    result = text
    codes: list[int] = []

    if styles.get("inverse"):
        codes.append(7)
    if styles.get("strikethrough"):
        codes.append(9)
    if styles.get("underline"):
        codes.append(4)
    if styles.get("italic"):
        codes.append(3)
    if styles.get("bold"):
        codes.append(1)
    if styles.get("dim"):
        codes.append(2)

    if codes:
        result = f"\x1b[{';'.join(str(c) for c in codes)}m{result}\x1b[0m"

    if styles.get("color"):
        result = colorize(result, styles["color"], "foreground")
    if styles.get("backgroundColor"):
        result = colorize(result, styles["backgroundColor"], "background")

    return result


def applyColor(text: str, color: Color | None) -> str:
    if not color:
        return text
    return colorize(text, color, "foreground")


apply_text_styles = applyTextStyles
apply_color = applyColor
