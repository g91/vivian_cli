"""MessageResponse component — mirrors src/components/MessageResponse.tsx."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
class MessageResponse:
    children: Any
    height: int | None = None

    def render_lines(self) -> list[str]:
        lines = _coerce_lines(self.children)
        if not lines:
            return []
        rendered = [f"  |_ {lines[0]}"]
        rendered.extend(f"     {line}" for line in lines[1:])
        if self.height is not None:
            return rendered[: self.height]
        return rendered


def renderMessageResponse(children: Any, height: int | None = None) -> list[str]:
    return MessageResponse(children=children, height=height).render_lines()


__all__ = ["MessageResponse", "renderMessageResponse"]