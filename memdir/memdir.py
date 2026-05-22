"""Core memdir helpers — mirrors src/memdir/memdir.ts."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ENTRYPOINT_NAME = "MEMORY.md"
MAX_ENTRYPOINT_LINES = 200
MAX_ENTRYPOINT_BYTES = 25_000

DIR_EXISTS_GUIDANCE = (
    "Your memory directory exists. Use the memory tools to read, write, and update "
    "your persistent memory files."
)

DIRS_EXIST_GUIDANCE = (
    "Your memory directories exist. Use the memory tools to read, write, and update "
    "your persistent memory files across scopes."
)


@dataclass
class EntrypointTruncation:
    content: str
    truncated: bool
    original_lines: int
    original_bytes: int


def truncate_entrypoint_content(raw: str) -> EntrypointTruncation:
    original_bytes = len(raw.encode("utf-8"))
    lines = raw.splitlines(keepends=True)
    original_lines = len(lines)

    truncated_lines = lines[:MAX_ENTRYPOINT_LINES]
    joined = "".join(truncated_lines)

    # Also enforce byte limit
    if len(joined.encode("utf-8")) > MAX_ENTRYPOINT_BYTES:
        # Trim by bytes
        encoded = raw.encode("utf-8")[:MAX_ENTRYPOINT_BYTES]
        joined = encoded.decode("utf-8", errors="replace")
        truncated = True
    else:
        truncated = len(lines) > MAX_ENTRYPOINT_LINES

    return EntrypointTruncation(
        content=joined,
        truncated=truncated,
        original_lines=original_lines,
        original_bytes=original_bytes,
    )


def ensure_memory_dir_exists(memory_dir: str) -> None:
    Path(memory_dir).mkdir(parents=True, exist_ok=True)
    entrypoint = Path(memory_dir) / ENTRYPOINT_NAME
    if not entrypoint.exists():
        entrypoint.write_text(
            "# Memory\n\nThis file is the entrypoint for your persistent memory.\n"
        )


def buildSearchingPastContextSection(auto_mem_dir: str):
    """Build the 'Searching past context' section for memory prompts."""
    return [
        "## Searching past context",
        "",
        f"When you need context beyond what's in the current conversation, search your memory directory at `{auto_mem_dir}`. "
        "Use glob patterns like `**/*.md` to find relevant files, then read the most promising ones.",
        "",
        "- Search by topic keywords, not by date",
        "- Prefer recent memories over old ones when they conflict",
        "- If you find nothing relevant, say so rather than guessing",
    ]
