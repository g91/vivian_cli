"""Permission dialog — minimal port of src/components/permissions/PermissionDialog.tsx."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..design_system import Pane


@dataclass(slots=True)
class PermissionDialog:
    title: str
    children: Any
    subtitle: Any = None
    color: str = "permission"
    titleColor: str | None = None
    innerPaddingX: int = 1
    workerBadge: Any = None
    titleRight: Any = None

    def render_lines(self) -> list[str]:
        lines = [self.title]
        if self.subtitle not in (None, False, ""):
            lines.append(str(self.subtitle))
        if self.titleRight not in (None, False, ""):
            lines.append(str(self.titleRight))
        children = self.children
        if hasattr(children, "render_lines"):
            lines.extend(children.render_lines())
        elif isinstance(children, list):
            lines.extend(str(line) for line in children)
        elif children not in (None, False, ""):
            lines.append(str(children))
        return Pane(children=lines, color=self.color).render_lines()


__all__ = ["PermissionDialog"]