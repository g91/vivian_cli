"""TUI module — Rich-based terminal UI matching the original vivian Code look."""

from .theme import Theme, get_theme, theme_to_rich_style, DARK_THEME, LIGHT_THEME, ThemeName
from .buddy import BuddyManager
from .renderer import (
    render_statusline,
    render_message,
    render_messages,
    render_spinner,
    render_prompt_input,
    render_header,
    build_layout,
)
from .app import VivianTUI

__all__ = [
    "Theme",
    "get_theme",
    "theme_to_rich_style",
    "DARK_THEME",
    "LIGHT_THEME",
    "ThemeName",
    "BuddyManager",
    "render_statusline",
    "render_message",
    "render_messages",
    "render_spinner",
    "render_prompt_input",
    "render_header",
    "build_layout",
    "VivianTUI",
]
