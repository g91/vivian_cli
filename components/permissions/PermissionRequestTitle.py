"""Compact permission request title block."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class PermissionRequestTitle:
    title: str
    subtitle: Any = None
    color: str = "permission"
    workerBadge: Any = None

    def render_lines(self) -> list[str]:
        header = self.title
        badge_name = None
        if self.workerBadge is not None:
            badge_name = getattr(self.workerBadge, "name", None)
            if badge_name is None and isinstance(self.workerBadge, dict):
                badge_name = self.workerBadge.get("name")
        if badge_name:
            header = f"{header} · @{badge_name}"
        lines = [header]
        if self.subtitle not in (None, False, ""):
            lines.append(str(self.subtitle))
        return lines


__all__ = ["PermissionRequestTitle"]