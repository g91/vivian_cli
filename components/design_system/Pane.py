"""Pane component — minimal port of src/components/design-system/Pane.tsx."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...context.modalContext import useIsInsideModal
from .Divider import Divider


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
    return [str(children)]


@dataclass(slots=True)
class Pane:
    children: Any
    color: str | None = None

    def render_lines(self) -> list[str]:
        lines = _coerce_lines(self.children)
        if useIsInsideModal():
            return [f" {line}" for line in lines]
        return [Divider(color=self.color), "", *[f"  {line}" for line in lines]]


__all__ = ["Pane"]