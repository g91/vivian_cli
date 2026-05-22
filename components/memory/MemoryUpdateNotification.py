"""MemoryUpdateNotification component — mirrors src/components/memory/MemoryUpdateNotification.tsx."""

from __future__ import annotations

from dataclasses import dataclass
from os import path as ospath
from pathlib import Path

from ...utils.cwd import get_cwd


def getRelativeMemoryPath(path: str) -> str:
    home_dir = str(Path.home())
    cwd = get_cwd()

    relative_to_home = f"~{path[len(home_dir):]}" if path.startswith(home_dir) else None
    relative_to_cwd = f"./{ospath.relpath(path, cwd)}" if path.startswith(cwd) else None

    if relative_to_home and relative_to_cwd:
        return relative_to_home if len(relative_to_home) <= len(relative_to_cwd) else relative_to_cwd
    return relative_to_home or relative_to_cwd or path


@dataclass(slots=True)
class MemoryUpdateNotification:
    memoryPath: str

    def render_lines(self) -> list[str]:
        display_path = getRelativeMemoryPath(self.memoryPath)
        return [f"Memory updated in {display_path} · /memory to edit"]


__all__ = ["MemoryUpdateNotification", "getRelativeMemoryPath"]