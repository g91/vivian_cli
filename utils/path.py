"""Path utilities — mirrors src/utils/path.ts"""
from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath


def expand_path(path: str, base_dir: str | None = None) -> str:
    """Expand ~ and resolve relative paths against base_dir (or cwd)."""
    expanded = os.path.expanduser(path)
    if os.path.isabs(expanded):
        return str(Path(expanded).resolve())
    base = base_dir or os.getcwd()
    return str(Path(base) / expanded)


def to_relative_path(path: str, base_dir: str | None = None) -> str:
    """Return path relative to base_dir (or cwd). Falls back to absolute."""
    base = base_dir or os.getcwd()
    try:
        return str(Path(path).relative_to(base))
    except ValueError:
        return path


def get_directory_for_path(path: str) -> str:
    """Return the directory containing path, or path itself if it's a directory."""
    p = Path(path)
    if p.is_dir():
        return str(p)
    return str(p.parent)


def contains_path_traversal(path: str) -> bool:
    """Return True if path contains traversal sequences like '..' or null bytes."""
    if "\x00" in path:
        return True
    normalized = PurePosixPath(path)
    for part in normalized.parts:
        if part == "..":
            return True
    return False


def normalize_path_for_config_key(path: str) -> str:
    """Normalize a path for use as a config dict key.

    Expands home, resolves, and replaces path separators with underscores.
    """
    resolved = str(Path(os.path.expanduser(path)).resolve())
    # Replace OS-specific separators to produce a stable key
    return resolved.replace(os.sep, "_").lstrip("_")


def sanitize_path(path: str) -> str:
    sanitized = os.path.realpath(path)
    return sanitized.replace(os.sep, "-").lstrip("-")


expandPath = expand_path
toRelativePath = to_relative_path
getDirectoryForPath = get_directory_for_path
containsPathTraversal = contains_path_traversal
normalizePathForConfigKey = normalize_path_for_config_key
sanitizePath = sanitize_path
