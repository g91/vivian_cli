"""
Port of src/utils/renderOptions.ts
"""
from __future__ import annotations

from typing import Any
import os
import sys

from .debug import log_error
from .envUtils import is_env_truthy


_UNSET = object()
_cached_stdin_override: Any = _UNSET


def getStdinOverride():
    """Gets a ReadStream for /dev/tty when stdin is piped.
This allows interactive Ink rendering even when stdin is a pipe.
Result is cached for the lifetime of the process."""
    global _cached_stdin_override
    if _cached_stdin_override is not _UNSET:
        return _cached_stdin_override

    if getattr(sys.stdin, "isatty", lambda: False)():
        _cached_stdin_override = None
        return None

    if is_env_truthy(os.environ.get("CI")):
        _cached_stdin_override = None
        return None

    if "mcp" in sys.argv:
        _cached_stdin_override = None
        return None

    if sys.platform == "win32":
        _cached_stdin_override = None
        return None

    try:
        tty_stream = open("/dev/tty", "r", encoding="utf-8", errors="ignore")
        _cached_stdin_override = tty_stream
        return tty_stream
    except Exception as error:
        log_error("Failed to open /dev/tty for stdin override", error)
        _cached_stdin_override = None
        return None


def getBaseRenderOptions(exitOnCtrlC=False):
    """Returns base render options for Ink, including stdin override when needed.
Use this for all render() calls to ensure piped input works correctly.

@param exitOnCtrlC - Whether to exit on Ctrl+C (usually false for dialogs)"""
    options = {"exitOnCtrlC": bool(exitOnCtrlC)}
    stdin = getStdinOverride()
    if stdin is not None:
        options["stdin"] = stdin
    return options


get_stdin_override = getStdinOverride
get_base_render_options = getBaseRenderOptions

