"""Ratchet component — minimal port of src/components/design-system/Ratchet.tsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...ink.hooks.use_terminal_viewport import useTerminalViewport


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
class Ratchet:
    children: Any
    lock: str = "always"
    _max_height: int = field(default=0, init=False)

    def render_lines(self) -> list[str]:
        lines = _coerce_lines(self.children)
        viewport = useTerminalViewport()
        self._max_height = max(self._max_height, min(len(lines), viewport["height"]))
        if self.lock in {"always", "offscreen"}:
            padded = list(lines)
            while len(padded) < self._max_height:
                padded.append("")
            return padded
        return lines


__all__ = ["Ratchet"]