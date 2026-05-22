"""File watcher — mirrors src/hooks/useFileWatcher.ts."""
from __future__ import annotations
from typing import Any, Callable

def useFileWatcher(path: str = "", onChange: Callable | None = None) -> dict[str, Any]:
    """Watch file for changes."""
    return {
        "path": path,
        "watching": False,
        "onChange": onChange,
        "watch": lambda p: None,
        "unwatch": lambda: None,
    }

use_file_watcher = useFileWatcher
