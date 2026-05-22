"""Theme-aware box helpers — minimal port of src/components/design-system/ThemedBox.tsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...utils.theme import Theme, getTheme
from .ThemeProvider import useTheme
from .ThemedText import resolveColor


def _coerce_lines(children: Any) -> list[str]:
    if children is None:
        return []
    if isinstance(children, str):
        return [children]
    if isinstance(children, list):
        return [str(line) for line in children]
    render_lines = getattr(children, "render_lines", None)
    if callable(render_lines):
        return [str(line) for line in render_lines()]
    render = getattr(children, "render", None)
    if callable(render):
        return [str(render())]
    return [str(children)]


@dataclass(slots=True)
class ThemedBox:
    children: Any = None
    borderColor: str | None = None
    borderTopColor: str | None = None
    borderBottomColor: str | None = None
    borderLeftColor: str | None = None
    borderRightColor: str | None = None
    backgroundColor: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def resolved_colors(self) -> dict[str, str]:
        theme_name = useTheme()[0]
        theme: Theme = getTheme(theme_name)
        resolved: dict[str, str] = {}
        for key in (
            "borderColor",
            "borderTopColor",
            "borderBottomColor",
            "borderLeftColor",
            "borderRightColor",
            "backgroundColor",
        ):
            value = getattr(self, key)
            color = resolveColor(value, theme)
            if color:
                resolved[key] = color
        return resolved

    def render_lines(self) -> list[str]:
        lines = _coerce_lines(self.children)
        colors = self.resolved_colors()
        if not colors:
            return lines
        prefix = " ".join(f"{key}={value}" for key, value in colors.items())
        return [f"<{prefix}> {line}" if line else f"<{prefix}>" for line in lines or [""]]


__all__ = ["ThemedBox"]