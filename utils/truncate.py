"""Truncation utilities — mirrors src/utils/truncate.ts"""
from __future__ import annotations


def truncate_path_middle(path: str, max_length: int) -> str:
    """Truncate a file path in the middle to preserve directory and filename.
    Example: 'src/components/deeply/nested/folder/MyComponent.py' →
             'src/components/…/MyComponent.py'
    """
    if len(path) <= max_length:
        return path
    if max_length <= 0:
        return "…"
    if max_length < 5:
        return path[:max_length]

    last_slash = path.rfind("/")
    filename = path[last_slash:] if last_slash >= 0 else path
    directory = path[:last_slash] if last_slash >= 0 else ""

    if len(filename) >= max_length - 1:
        # Filename alone is too long, truncate from start
        return "…" + path[-(max_length - 1):]

    available_for_dir = max_length - 1 - len(filename)
    if available_for_dir <= 0:
        return "…" + filename[-(max_length - 1):]

    truncated_dir = directory[:available_for_dir]
    return truncated_dir + "…" + filename


def truncate_to_width(text: str, max_width: int) -> str:
    """Truncate text to fit within max_width characters, appending '…'."""
    if len(text) <= max_width:
        return text
    if max_width <= 1:
        return "…"
    return text[: max_width - 1] + "…"


def truncate_start_to_width(text: str, max_width: int) -> str:
    """Truncate text from the start to fit within max_width, prepending '…'."""
    if len(text) <= max_width:
        return text
    if max_width <= 1:
        return "…"
    return "…" + text[-(max_width - 1):]
