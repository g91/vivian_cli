"""List item component — mirrors src/components/design-system/ListItem.tsx."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


POINTER = "❯"
ARROW_DOWN = "↓"
ARROW_UP = "↑"
TICK = "✓"


@dataclass(slots=True)
class ListItem:
    isFocused: bool
    children: Any
    isSelected: bool = False
    description: str | None = None
    showScrollDown: bool = False
    showScrollUp: bool = False
    styled: bool = True
    disabled: bool = False
    declareCursor: bool = True

    def _indicator(self) -> str:
        if self.disabled:
            return " "
        if self.isFocused:
            return POINTER
        if self.showScrollDown:
            return ARROW_DOWN
        if self.showScrollUp:
            return ARROW_UP
        return " "

    def render_lines(self) -> list[str]:
        main = str(self.children)
        selected = f" {TICK}" if self.isSelected and not self.disabled else ""
        lines = [f"{self._indicator()} {main}{selected}"]
        if self.description:
            lines.append(f"  {self.description}")
        return lines


__all__ = ["ListItem"]