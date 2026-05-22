"""Status icon component — mirrors src/components/design-system/StatusIcon.tsx."""

from __future__ import annotations


STATUS_CONFIG = {
    "success": {"icon": "✓", "color": "success"},
    "error": {"icon": "✗", "color": "error"},
    "warning": {"icon": "⚠", "color": "warning"},
    "info": {"icon": "ℹ", "color": "suggestion"},
    "pending": {"icon": "○", "color": None},
    "loading": {"icon": "…", "color": None},
}


def StatusIcon(status: str, withSpace: bool = False) -> str:
    config = STATUS_CONFIG[status]
    return f"{config['icon']}{' ' if withSpace else ''}"


__all__ = ["StatusIcon", "STATUS_CONFIG"]