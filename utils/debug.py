"""Debug logging utilities — mirrors src/utils/debug.ts"""
from __future__ import annotations

import os
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from ..bootstrap.state import getSessionId
from .envUtils import get_vivian_config_home_dir

DebugLogLevel = Literal["verbose", "debug", "info", "warn", "error"]

_LEVEL_ORDER: dict[str, int] = {
    "verbose": 0,
    "debug": 1,
    "info": 2,
    "warn": 3,
    "error": 4,
}

_runtime_debug_enabled = False


@lru_cache(maxsize=1)
def get_min_debug_log_level() -> str:
    raw = os.environ.get("vivian_CODE_DEBUG_LOG_LEVEL", "").lower().strip()
    if raw in _LEVEL_ORDER:
        return raw
    return "debug"


def enable_debug_mode() -> None:
    global _runtime_debug_enabled
    _runtime_debug_enabled = True
    is_debug_mode.cache_clear()


@lru_cache(maxsize=1)
def is_debug_mode() -> bool:
    return (
        _runtime_debug_enabled
        or os.environ.get("DEBUG") in ("1", "true", "yes")
        or os.environ.get("DEBUG_SDK") in ("1", "true", "yes")
        or "--debug" in sys.argv
        or "-d" in sys.argv
        or get_debug_file_path() is not None
    )


@lru_cache(maxsize=1)
def get_debug_file_path() -> str | None:
    for index, arg in enumerate(sys.argv):
        if arg.startswith("--debug-file="):
            return arg.split("=", 1)[1]
        if arg == "--debug-file" and index + 1 < len(sys.argv):
            return sys.argv[index + 1]

    logs_dir = os.environ.get("vivian_CODE_DEBUG_LOGS_DIR")
    if logs_dir:
        return str(Path(logs_dir) / f"{getSessionId()}.txt")

    return str(Path(get_vivian_config_home_dir()) / "debug" / f"{getSessionId()}.txt")


def _write_debug_log(output: str) -> None:
    path = get_debug_file_path()
    if not path:
        return
    try:
        debug_path = Path(path)
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        with debug_path.open("a", encoding="utf-8") as handle:
            handle.write(output)
    except Exception:
        pass


def log_for_debugging(message: str, level: str = "debug") -> None:
    """Write a debug message to the session debug log when debug mode is enabled."""
    if not is_debug_mode():
        return
    min_level = get_min_debug_log_level()
    if _LEVEL_ORDER.get(level, 1) < _LEVEL_ORDER.get(min_level, 1):
        return
    ts = time.strftime("%H:%M:%S")
    _write_debug_log(f"[{ts}] [{level.upper()}] {message}\n")


def log_error(message: str, error: Optional[Exception] = None) -> None:
    """Log an error message unconditionally to stderr."""
    if error:
        sys.stderr.write(f"[ERROR] {message}: {error}\n")
    else:
        sys.stderr.write(f"[ERROR] {message}\n")
    sys.stderr.flush()


getMinDebugLogLevel = get_min_debug_log_level
enableDebugMode = enable_debug_mode
isDebugMode = is_debug_mode
getDebugFilePath = get_debug_file_path
logForDebugging = log_for_debugging
logError = log_error
