"""Memory file scanner — mirrors src/memdir/memoryScan.ts."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

MAX_MEMORY_FILES = 200
ENTRYPOINT_NAME = "MEMORY.md"


@dataclass
class MemoryHeader:
    filename: str
    file_path: str
    mtime_ms: float
    description: str
    type: str


def _parse_frontmatter(text: str) -> dict:
    """Extract YAML-like frontmatter from the top of a file."""
    result: dict = {}
    if not text.startswith("---"):
        return result
    end = text.find("---", 3)
    if end == -1:
        return result
    block = text[3:end]
    for line in block.splitlines():
        m = re.match(r"^(\w+)\s*:\s*(.+)$", line.strip())
        if m:
            result[m.group(1).strip()] = m.group(2).strip()
    return result


def scan_memory_files(memory_dir: str, _signal=None) -> list[MemoryHeader]:
    """Scan *memory_dir* for .md files, parse frontmatter, sort newest-first."""
    headers: list[MemoryHeader] = []
    try:
        entries = os.scandir(memory_dir)
    except OSError:
        return headers

    for entry in entries:
        if not entry.is_file():
            continue
        if not entry.name.endswith(".md"):
            continue
        if entry.name == ENTRYPOINT_NAME:
            continue
        try:
            stat = entry.stat()
            mtime_ms = stat.st_mtime * 1000
            text = Path(entry.path).read_text(errors="replace")[:4096]
            fm = _parse_frontmatter(text)
            headers.append(
                MemoryHeader(
                    filename=entry.name,
                    file_path=entry.path,
                    mtime_ms=mtime_ms,
                    description=fm.get("description", ""),
                    type=fm.get("type", "user"),
                )
            )
        except OSError:
            continue

    headers.sort(key=lambda h: h.mtime_ms, reverse=True)
    return headers[:MAX_MEMORY_FILES]


def format_memory_manifest(headers: list[MemoryHeader]) -> str:
    if not headers:
        return "(no memory files)"
    lines = []
    for h in headers:
        desc = f" — {h.description}" if h.description else ""
        lines.append(f"- {h.filename}{desc}")
    return "\n".join(lines)
