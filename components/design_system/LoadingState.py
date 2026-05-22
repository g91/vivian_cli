"""Loading state component — mirrors src/components/design-system/LoadingState.tsx."""

from __future__ import annotations

from dataclasses import dataclass

from ..Spinner import Spinner


@dataclass(slots=True)
class LoadingState:
    message: str
    bold: bool = False
    dimColor: bool = False
    subtitle: str | None = None

    def render_lines(self) -> list[str]:
        main_message = f"{Spinner()} {self.message}"
        lines = [main_message]
        if self.subtitle:
            lines.append(self.subtitle)
        return lines


__all__ = ["LoadingState"]