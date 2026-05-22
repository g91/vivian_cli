"""
Port of src/utils/streamJsonStdoutGuard.ts
"""
from __future__ import annotations

import json
import sys
from typing import Any, Callable

from .cleanupRegistry import register_cleanup
from .debug import logForDebugging


# Sentinel written to stderr ahead of any diverted non-JSON line, so that
STDOUT_GUARD_MARKER: Any = '[stdout-guard]'  # type: ignore

_installed = False
_buffer = ''
_original_write: Callable[[str], Any] | None = None


def isJsonLine(line):
    # Empty lines are tolerated in NDJSON streams — treat them as valid so a
    # trailing newline or a blank separator doesn't trip the guard.
    if len(line) == 0:
        return True
    try:
        json.loads(line)
        return True
    except Exception:
        return False


def installStreamJsonStdoutGuard():
    """Install a runtime guard on process.stdout.write for --output-format=stream-json."""
    global _installed, _original_write, _buffer
    if _installed:
        return
    _installed = True
    _original_write = sys.stdout.write

    def guarded_write(chunk: Any) -> Any:
        global _buffer
        text = chunk.decode('utf-8', errors='ignore') if isinstance(chunk, (bytes, bytearray)) else str(chunk)
        _buffer += text
        wrote = 0
        while True:
            newline_idx = _buffer.find('\n')
            if newline_idx == -1:
                break
            line = _buffer[:newline_idx]
            _buffer = _buffer[newline_idx + 1 :]
            if isJsonLine(line):
                wrote = _original_write(line + '\n') if _original_write else len(line) + 1
            else:
                sys.stderr.write(f'{STDOUT_GUARD_MARKER} {line}\n')
                sys.stderr.flush()
                logForDebugging(
                    f'streamJsonStdoutGuard diverted non-JSON stdout line: {line[:200]}'
                )
                wrote = len(line) + 1
        return wrote if wrote else len(text)

    sys.stdout.write = guarded_write

    async def _cleanup() -> None:
        global _buffer, _installed, _original_write
        if _buffer:
            if _original_write and isJsonLine(_buffer):
                _original_write(_buffer + '\n')
            else:
                sys.stderr.write(f'{STDOUT_GUARD_MARKER} {_buffer}\n')
                sys.stderr.flush()
            _buffer = ''
        if _original_write:
            sys.stdout.write = _original_write
            _original_write = None
        _installed = False

    register_cleanup(_cleanup)


def _resetStreamJsonStdoutGuardForTesting():
    """Testing-only reset. Restores the real stdout.write and clears the line"""
    global _buffer, _installed, _original_write
    if _original_write:
        sys.stdout.write = _original_write
        _original_write = None
    _buffer = ''
    _installed = False


install_stream_json_stdout_guard = installStreamJsonStdoutGuard
reset_stream_json_stdout_guard_for_testing = _resetStreamJsonStdoutGuardForTesting

