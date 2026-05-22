"""Process I/O helpers — mirrors src/utils/process.ts"""
from __future__ import annotations

import sys


def write_to_stdout(data: str) -> None:
    """Write data to stdout (ignores broken pipe)."""
    try:
        sys.stdout.write(data)
        sys.stdout.flush()
    except BrokenPipeError:
        pass


def write_to_stderr(data: str) -> None:
    """Write data to stderr (ignores broken pipe)."""
    try:
        sys.stderr.write(data)
        sys.stderr.flush()
    except BrokenPipeError:
        pass


def exit_with_error(message: str) -> "Never":  # type: ignore[return]
    """Write error to stderr and exit with code 1."""
    print(message, file=sys.stderr)
    sys.exit(1)


def register_process_output_error_handlers() -> None:
    """Register SIGPIPE-safe handlers for stdout/stderr (no-op on Python)."""
    # Python's BrokenPipeError is handled at the call sites above
    import logging as _log
    _log.debug("Called register_process_output_error_handlers")
    return
