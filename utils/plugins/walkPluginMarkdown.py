"""
Port of src/utils/plugins/walkPluginMarkdown.ts

Recursively walk a plugin directory, invoking on_file for each .md file.
"""
from __future__ import annotations

import os
import re
from typing import Callable, Awaitable, List


SKILL_MD_RE = re.compile(r"^skill\.md$", re.IGNORECASE)


async def walkPluginMarkdown(
    root_dir: str,
    on_file: Callable[[str, List[str]], Awaitable[None]],
    stop_at_skill_dir: bool = False,
    log_label: str = "plugin",
) -> None:
    """Recursively walk a plugin directory, invoking on_file for each .md file."""

    async def _scan(dir_path: str, namespace: List[str]) -> None:
        try:
            entries = list(os.scandir(dir_path))
        except OSError as e:
            try:
                from ..debug import logForDebugging
                logForDebugging(f"Failed to scan {log_label} directory {dir_path}: {e}", level="error")
            except Exception:
                pass
            return

        if stop_at_skill_dir:
            has_skill_md = any(e.is_file() and SKILL_MD_RE.match(e.name) for e in entries)
            if has_skill_md:
                for entry in entries:
                    if entry.is_file() and entry.name.lower().endswith(".md"):
                        await on_file(os.path.join(dir_path, entry.name), namespace)
                return

        for entry in entries:
            full_path = os.path.join(dir_path, entry.name)
            if entry.is_dir():
                await _scan(full_path, [*namespace, entry.name])
            elif entry.is_file() and entry.name.lower().endswith(".md"):
                await on_file(full_path, namespace)

    await _scan(root_dir, [])

