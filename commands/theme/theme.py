"""theme command — mirrors src/commands/theme/theme.tsx.

Non-interactive fallback for the theme picker command.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult

THEMES = {
    "auto": "Auto (match terminal)",
    "dark": "Dark mode",
    "light": "Light mode",
    "dark-daltonized": "Dark mode (colorblind-friendly)",
    "light-daltonized": "Light mode (colorblind-friendly)",
    "dark-ansi": "Dark mode (ANSI colors only)",
    "light-ansi": "Light mode (ANSI colors only)",
}


def setTheme(theme_name: str) -> str:
    """Set the UI theme."""
    if theme_name in THEMES:
        return f"Theme set to {theme_name}"
    return f"Unknown theme: {theme_name}. Available: {', '.join(THEMES)}"


def getTheme() -> str:
    """Get current theme."""
    from ...utils.config import get_global_config

    theme = get_global_config().get("theme")
    return theme if theme in THEMES else "dark"


async def call(args: str, context: CommandContext) -> TextResult:
    """View or change the theme."""
    from ...types.command import TextResult
    from ...components.design_system import useTheme
    from ...utils.config import save_global_config

    theme = args.strip().lower() if args else ""

    if not theme:
        current = getTheme()
        lines = [f"Current theme setting: {current}", "", "Available theme settings:"]
        for name, desc in THEMES.items():
            marker = " ← current" if name == current else ""
            lines.append(f"  {name:<15} {desc}{marker}")
        return TextResult("\n".join(lines))

    if theme in {"help", "-h", "--help"}:
        return TextResult("Usage: /theme [auto|dark|light|dark-daltonized|light-daltonized|dark-ansi|light-ansi]")

    if theme not in THEMES:
        return TextResult(setTheme(theme))

    try:
        _, set_theme = useTheme()
        set_theme(theme)
    except Exception:
        pass

    try:
        save_global_config(lambda current: {**current, "theme": theme})
    except Exception:
        pass

    return TextResult(setTheme(theme))


set_theme = setTheme
get_theme = getTheme
