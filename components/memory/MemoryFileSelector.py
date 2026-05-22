"""MemoryFileSelector component — mirrors src/components/memory/MemoryFileSelector.tsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ...bootstrap.state import getOriginalCwd
from ...utils.cwd import get_cwd


@dataclass(slots=True)
class MemoryFileInfo:
    path: str
    type: str
    content: str = ""
    exists: bool = True
    parent: str | None = None
    isNested: bool = False


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def getDefaultMemoryPaths() -> list[MemoryFileInfo]:
    original_cwd = Path(getOriginalCwd() or get_cwd())
    user_root = Path.home() / ".vivian"
    project_memory = original_cwd / "vivian.md"
    user_memory = user_root / "vivian.md"

    entries: list[MemoryFileInfo] = []
    for file_path, kind in ((user_memory, "User"), (project_memory, "Project")):
        entries.append(
            MemoryFileInfo(
                path=str(file_path),
                type=kind,
                content=_read_text(file_path),
                exists=file_path.exists(),
            )
        )

    for scope_root, kind in ((user_root / "memories", "User"), (original_cwd / ".vivian" / "memories", "Project")):
        if not scope_root.exists():
            continue
        for memory_file in sorted(scope_root.rglob("*.md")):
            parent = str(memory_file.parent) if memory_file.parent != scope_root else None
            entries.append(
                MemoryFileInfo(
                    path=str(memory_file),
                    type=kind,
                    content=_read_text(memory_file),
                    exists=True,
                    parent=parent,
                    isNested=parent is not None,
                )
            )
    deduped: dict[str, MemoryFileInfo] = {entry.path: entry for entry in entries}
    return list(deduped.values())


def _display_path(path: str) -> str:
    home = str(Path.home())
    cwd = str(Path(getOriginalCwd() or get_cwd()))
    if path.startswith(cwd):
        return f"./{Path(path).relative_to(cwd)}"
    if path.startswith(home):
        return f"~{path[len(home):]}"
    return path


def buildMemoryFileOptions(files: list[MemoryFileInfo] | None = None) -> list[dict[str, str]]:
    user_memory_path = str(Path.home() / ".vivian" / "vivian.md")
    project_memory_path = str(Path(getOriginalCwd() or get_cwd()) / "vivian.md")
    options: list[dict[str, str]] = []
    for file in files or getDefaultMemoryPaths():
        exists_label = "" if file.exists else " (new)"
        if file.type == "User" and not file.isNested and file.path == user_memory_path:
            label = "User memory"
            description = "Saved in ~/.vivian/vivian.md"
        elif file.type == "Project" and not file.isNested and file.path == project_memory_path:
            label = "Project memory"
            description = "Saved in ./vivian.md"
        else:
            label = f"{_display_path(file.path)}{exists_label}"
            description = "@-imported" if file.parent else ("dynamically loaded" if file.isNested else "")
        options.append({"label": label, "value": file.path, "description": description})
    return options


@dataclass(slots=True)
class MemoryFileSelector:
    onSelect: Callable[[str], None]
    onCancel: Callable[[], None]
    files: list[MemoryFileInfo] = field(init=False)
    options: list[dict[str, str]] = field(init=False)

    def __post_init__(self) -> None:
        self.files = getDefaultMemoryPaths()
        self.options = buildMemoryFileOptions(self.files)

    def render_lines(self) -> list[str]:
        lines = ["Select a memory file:", ""]
        for index, option in enumerate(self.options, start=1):
            suffix = f" - {option['description']}" if option["description"] else ""
            lines.append(f"[{index}] {option['label']}{suffix}")
        lines.append("")
        lines.append("[0] Cancel")
        return lines

    def select(self, value: str) -> str | None:
        if value in {"0", "cancel", "esc"}:
            self.onCancel()
            return None
        chosen = None
        if value.isdigit():
            index = int(value) - 1
            if 0 <= index < len(self.options):
                chosen = self.options[index]["value"]
        else:
            for option in self.options:
                if option["value"] == value:
                    chosen = option["value"]
                    break
        if chosen is None:
            raise ValueError(f"Unknown memory selection: {value}")
        self.onSelect(chosen)
        return chosen
