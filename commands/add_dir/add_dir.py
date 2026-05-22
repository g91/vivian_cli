"""add-dir command — mirrors src/commands/add-dir/add-dir.tsx.

Adds a directory to the workspace context for the AI to access.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def addDirectory(path: str) -> str:
    """Validate and add a directory path."""
    if not path:
        return "Usage: /add-dir <path>"
    expanded = os.path.expanduser(path)
    abs_path = os.path.abspath(expanded)
    if not os.path.exists(abs_path):
        return f"Path not found: {abs_path}"
    if not os.path.isdir(abs_path):
        return f"Not a directory: {abs_path}"
    return f"Added directory: {abs_path}"


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    path = args.strip() if args else ""
    result = addDirectory(path)
    if result.startswith("Added"):
        try:
            dirs = getattr(context, "config", {}).get("workspace_dirs", [])
            expanded = os.path.abspath(os.path.expanduser(path))
            if expanded not in dirs:
                dirs.append(expanded)
                if hasattr(context, "set_setting"):
                    context.set_setting("workspace_dirs", dirs)
        except Exception:
            pass
    return TextResult(result)


add_directory = addDirectory
