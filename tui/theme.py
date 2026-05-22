"""Theme system — mirrors src/utils/theme.ts and src/components/design-system/.

Provides dark/light themes with the exact same semantic color keys as the original.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ThemeName = Literal["dark", "light"]
ThemeSetting = Literal["dark", "light", "auto"]


@dataclass
class Theme:
    """Semantic color theme matching the original TypeScript Theme type."""

    # Primary brand
    vivian: str = "#D97706"  # Warm amber/orange — the vivian brand color
    vivianShimmer: str = "#F59E0B"  # Lighter shimmer variant

    # System spinner (blue variant)
    vivianBlue_FOR_SYSTEM_SPINNER: str = "#3B82F6"
    vivianBlueShimmer_FOR_SYSTEM_SPINNER: str = "#60A5FA"

    # Permission
    permission: str = "#A855F7"  # Purple
    permissionShimmer: str = "#C084FC"

    # Plan mode
    planMode: str = "#06B6D4"  # Cyan

    # IDE
    ide: str = "#6366F1"  # Indigo

    # Auto-accept
    autoAccept: str = "#22C55E"  # Green

    # Prompt border
    promptBorder: str = "#6B7280"
    promptBorderShimmer: str = "#9CA3AF"

    # Text
    text: str = "#F9FAFB"
    inverseText: str = "#111827"
    inactive: str = "#6B7280"
    inactiveShimmer: str = "#9CA3AF"
    subtle: str = "#4B5563"
    suggestion: str = "#93C5FD"  # Light blue
    remember: str = "#FDE68A"  # Light yellow

    # Background
    background: str = "#111827"

    # Semantic
    success: str = "#22C55E"
    error: str = "#EF4444"
    warning: str = "#F59E0B"
    warningShimmer: str = "#FBBF24"
    merged: str = "#8B5CF6"

    # Diff
    diffAdded: str = "#22C55E"
    diffRemoved: str = "#EF4444"
    diffAddedDimmed: str = "#166534"
    diffRemovedDimmed: str = "#991B1B"
    diffAddedWord: str = "#14532D"
    diffRemovedWord: str = "#7F1D1D"

    # Agent colors
    red_FOR_SUBAGENTS_ONLY: str = "#EF4444"
    blue_FOR_SUBAGENTS_ONLY: str = "#3B82F6"
    green_FOR_SUBAGENTS_ONLY: str = "#22C55E"
    yellow_FOR_SUBAGENTS_ONLY: str = "#EAB308"
    purple_FOR_SUBAGENTS_ONLY: str = "#A855F7"
    orange_FOR_SUBAGENTS_ONLY: str = "#F97316"
    pink_FOR_SUBAGENTS_ONLY: str = "#EC4899"
    cyan_FOR_SUBAGENTS_ONLY: str = "#06B6D4"

    # Bash border
    bashBorder: str = "#374151"
    bashMessageBackgroundColor: str = "#1F2937"

    # Memory
    memoryBackgroundColor: str = "#1E1B4B"

    # Rate limits
    rate_limit_fill: str = "#22C55E"
    rate_limit_empty: str = "#374151"

    # Fast mode
    fastMode: str = "#F59E0B"
    fastModeShimmer: str = "#FBBF24"

    # Brief/assistant labels
    briefLabelYou: str = "#6B7280"
    briefLabelvivian: str = "#D97706"

    # Rainbow for ultrathink
    rainbow_red: str = "#EF4444"
    rainbow_orange: str = "#F97316"
    rainbow_yellow: str = "#EAB308"
    rainbow_green: str = "#22C55E"
    rainbow_blue: str = "#3B82F6"
    rainbow_indigo: str = "#6366F1"

    # Chrome
    chromeYellow: str = "#F59E0B"

    # Professional blue (grove)
    professionalBlue: str = "#2563EB"

    # TUI V2
    clawd_body: str = "#D97706"
    clawd_background: str = "#1F2937"
    userMessageBackground: str = "#1E3A5F"
    userMessageBackgroundHover: str = "#1E4D8C"
    messageActionsBackground: str = "#1E3A5F"
    selectionBg: str = "#2563EB"

    # Rainbow
    rainbow_violet: str = "#8B5CF6"

    def get(self, key: str, default: str = "") -> str:
        return getattr(self, key, default)


# ── Theme Definitions ──────────────────────────────────────

DARK_THEME = Theme()

LIGHT_THEME = Theme(
    text="#111827",
    inverseText="#F9FAFB",
    inactive="#9CA3AF",
    inactiveShimmer="#D1D5DB",
    subtle="#D1D5DB",
    suggestion="#1D4ED8",
    remember="#92400E",
    background="#FFFFFF",
    bashBorder="#E5E7EB",
    bashMessageBackgroundColor="#F3F4F6",
    memoryBackgroundColor="#EDE9FE",
    rate_limit_empty="#E5E7EB",
    userMessageBackground="#DBEAFE",
    userMessageBackgroundHover="#BFDBFE",
    messageActionsBackground="#DBEAFE",
    selectionBg="#93C5FD",
    promptBorder="#D1D5DB",
    promptBorderShimmer="#E5E7EB",
    clawd_background="#F3F4F6",
)


def get_theme(name: ThemeName) -> Theme:
    """Get a theme by name."""
    if name == "light":
        return LIGHT_THEME
    return DARK_THEME


# ── Rich-compatible style mapping ──────────────────────────

def theme_to_rich_style(theme: Theme) -> dict[str, str]:
    """Convert Theme colors to Rich style strings."""
    return {
        "vivian": f"bold {theme.vivian}",
        "text": theme.text,
        "inactive": f"dim {theme.inactive}",
        "subtle": f"dim {theme.subtle}",
        "success": f"bold {theme.success}",
        "error": f"bold {theme.error}",
        "warning": f"bold {theme.warning}",
        "info": f"bold {theme.vivianBlue_FOR_SYSTEM_SPINNER}",
        "prompt": f"bold {theme.vivian}",
        "user": f"bold {theme.suggestion}",
        "assistant": theme.text,
        "system": f"dim {theme.inactive}",
        "border": theme.promptBorder,
        "border.focused": theme.vivian,
        "statusline": f"reverse {theme.text} on {theme.background}",
        "statusline.model": f"bold {theme.vivian}",
        "statusline.cost": theme.text,
        "statusline.mode": theme.permission,
        "statusline.context": theme.inactive,
        "diff.added": f"bold {theme.diffAdded}",
        "diff.removed": f"bold {theme.diffRemoved}",
        "agent.red": theme.red_FOR_SUBAGENTS_ONLY,
        "agent.blue": theme.blue_FOR_SUBAGENTS_ONLY,
        "agent.green": theme.green_FOR_SUBAGENTS_ONLY,
        "agent.yellow": theme.yellow_FOR_SUBAGENTS_ONLY,
        "agent.purple": theme.purple_FOR_SUBAGENTS_ONLY,
        "agent.orange": theme.orange_FOR_SUBAGENTS_ONLY,
        "agent.pink": theme.pink_FOR_SUBAGENTS_ONLY,
        "agent.cyan": theme.cyan_FOR_SUBAGENTS_ONLY,
        "fast": f"bold {theme.fastMode}",
        "plan": f"bold {theme.planMode}",
        "permission": f"bold {theme.permission}",
        "bash.border": theme.bashBorder,
        "memory.bg": theme.memoryBackgroundColor,
        "buddy.body": theme.clawd_body,
        "buddy.bg": theme.clawd_background,
    }
