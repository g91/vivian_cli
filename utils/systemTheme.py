"""Port of src/utils/systemTheme.ts."""
from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional


SystemTheme = str
Rgb = Dict[str, Any]

_cached_system_theme: Optional[SystemTheme] = None


def getSystemThemeName():
    """Get the current terminal theme. Cached after first detection; the watcher
updates the cache on live changes."""
    global _cached_system_theme
    if _cached_system_theme is None:
        _cached_system_theme = detectFromColorFgBg() or "dark"
    return _cached_system_theme


def setCachedSystemTheme(theme):
    """Update the cached terminal theme. Called by the watcher when the OSC 11
query returns so non-React call sites stay in sync."""
    global _cached_system_theme
    _cached_system_theme = theme


def resolveThemeSetting(setting):
    """Resolve a ThemeSetting (which may be 'auto') to a concrete ThemeName."""
    if setting == "auto":
        return getSystemThemeName()
    return setting


def themeFromOscColor(data):
    """Parse an OSC color response data string into a theme.

Accepts XParseColor formats returned by OSC 10/11 queries:
- `rgb:R/G/B` where each component is 1–4 hex digits (each scaled to
[0, 16^n - 1] for n digits). This is what xterm, iTerm2, Terminal.app,
Ghostty, kitty, Alacritty, etc. return.
- `#RRGGBB` / `#RRRRGGGGBBBB` (rare, but cheap to accept).

Returns undefined for unrecognized formats so callers can fall back."""
    rgb = parseOscRgb(data)
    if not rgb:
        return None
    luminance = 0.2126 * rgb["r"] + 0.7152 * rgb["g"] + 0.0722 * rgb["b"]
    return "light" if luminance > 0.5 else "dark"


def parseOscRgb(data):
    if not isinstance(data, str):
        return None
    rgb_match = re.match(r"^rgba?:([0-9a-f]{1,4})/([0-9a-f]{1,4})/([0-9a-f]{1,4})", data, re.IGNORECASE)
    if rgb_match:
        return {
            "r": hexComponent(rgb_match.group(1)),
            "g": hexComponent(rgb_match.group(2)),
            "b": hexComponent(rgb_match.group(3)),
        }
    hash_match = re.match(r"^#([0-9a-f]+)$", data, re.IGNORECASE)
    if hash_match:
        hex_value = hash_match.group(1)
        if len(hex_value) % 3 == 0:
            n = len(hex_value) // 3
            return {
                "r": hexComponent(hex_value[0:n]),
                "g": hexComponent(hex_value[n: 2 * n]),
                "b": hexComponent(hex_value[2 * n: 3 * n]),
            }
    return None


def hexComponent(hex):
    max = 16 ** len(hex) - 1
    return int(hex, 16) / max


def detectFromColorFgBg():
    """Read $COLORFGBG for a synchronous initial guess before the OSC 11
round-trip completes. Format is `fg;bg` (or `fg;other;bg`) where values
are ANSI color indices. rxvt convention: bg 0–6 or 8 are dark; bg 7
and 9–15 are light. Only set by some terminals (rxvt-family, Konsole,
iTerm2 with the option enabled), so this is a best-effort hint."""
    colorfgbg = os.environ.get("COLORFGBG")
    if not colorfgbg:
        return None
    parts = colorfgbg.split(";")
    if not parts:
        return None
    bg = parts[-1]
    if bg == "":
        return None
    try:
        bg_num = int(bg)
    except ValueError:
        return None
    if bg_num < 0 or bg_num > 15:
        return None
    return "dark" if bg_num <= 6 or bg_num == 8 else "light"


get_system_theme_name = getSystemThemeName
set_cached_system_theme = setCachedSystemTheme
resolve_theme_setting = resolveThemeSetting
theme_from_osc_color = themeFromOscColor
parse_osc_rgb = parseOscRgb
hex_component = hexComponent
detect_from_color_fg_bg = detectFromColorFgBg

