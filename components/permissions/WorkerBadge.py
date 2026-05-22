"""Compact worker badge for permission prompts."""

from __future__ import annotations

from dataclasses import dataclass

from ...constants.figures import BLACK_CIRCLE


@dataclass(slots=True)
class WorkerBadge:
    name: str
    color: str

    def render_lines(self) -> list[str]:
        prefix = f"[{self.color}] " if self.color else ""
        return [f"{prefix}{BLACK_CIRCLE} @{self.name}"]


__all__ = ["WorkerBadge"]