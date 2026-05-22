"""
Port of src/utils/ink.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, TypeVar, List, Dict, Tuple, Set, cast, overload, TYPE_CHECKING




DEFAULT_AGENT_THEME_COLOR = 'cyan_FOR_SUBAGENTS_ONLY'

"""
Convert a color string to Ink's TextProps['color'] format.
Colors are typically AgentColorName values like 'blue', 'green', etc.
This converts them to theme keys so they respect the current theme.
Falls back to the raw ANSI color if the color is not a known agent color.
"""
def toInkColor(color):
    if not color:
        return DEFAULT_AGENT_THEME_COLOR
    # Try to map to a theme color if it's a known agent color
    themeColor = AGENT_COLOR_TO_THEME_COLOR[color]
    if themeColor:
        return themeColor
    # Fall back to raw ANSI color for unknown colors
    return f"ansi:{color}"['color']
