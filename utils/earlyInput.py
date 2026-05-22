"""
Port of src/utils/earlyInput.ts
"""
from __future__ import annotations

import os
import select
import sys
import threading

from .intl import last_grapheme


_early_input_buffer = ""
_is_capturing = False
_read_thread: threading.Thread | None = None
_stop_event = threading.Event()
_buffer_lock = threading.Lock()


def _stdin_read_loop() -> None:
    while _is_capturing and not _stop_event.is_set():
        try:
            readable, _, _ = select.select([sys.stdin], [], [], 0.05)
        except Exception:
            break
        if not readable:
            continue
        try:
            chunk = os.read(sys.stdin.fileno(), 1024)
        except Exception:
            break
        if not chunk:
            stopCapturingEarlyInput()
            break
        try:
            processChunk(chunk.decode("utf-8", errors="ignore"))
        except SystemExit:
            raise
        except Exception:
            continue


def startCapturingEarlyInput():
    """Start capturing stdin data early, before the REPL is initialized.
Should be called as early as possible in the startup sequence.

Only captures if stdin is a TTY (interactive terminal)."""
    global _is_capturing, _early_input_buffer, _read_thread
    if (
        not getattr(sys.stdin, "isatty", lambda: False)()
        or _is_capturing
        or "-p" in sys.argv
        or "--print" in sys.argv
    ):
        return

    _is_capturing = True
    _early_input_buffer = ""
    _stop_event.clear()

    try:
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

    try:
        _read_thread = threading.Thread(target=_stdin_read_loop, daemon=True)
        _read_thread.start()
    except Exception:
        _is_capturing = False


def processChunk(str):
    """Process a chunk of input data"""
    global _early_input_buffer
    i = 0
    while i < len(str):
        char = str[i]
        code = ord(char)
        if code == 3:
            stopCapturingEarlyInput()
            raise SystemExit(130)
        if code == 4:
            stopCapturingEarlyInput()
            return
        if code in (127, 8):
            with _buffer_lock:
                if _early_input_buffer:
                    last = last_grapheme(_early_input_buffer)
                    _early_input_buffer = _early_input_buffer[: -(len(last) or 1)]
            i += 1
            continue
        if code == 27:
            i += 1
            while i < len(str) and not (64 <= ord(str[i]) <= 126):
                i += 1
            if i < len(str):
                i += 1
            continue
        if code < 32 and code not in (9, 10, 13):
            i += 1
            continue
        with _buffer_lock:
            _early_input_buffer += "\n" if code == 13 else char
        i += 1


def stopCapturingEarlyInput():
    """Stop capturing early input.
Called automatically when input is consumed, or can be called manually."""
    global _is_capturing
    if not _is_capturing:
        return
    _is_capturing = False
    _stop_event.set()


def consumeEarlyInput():
    """Consume any early input that was captured.
Returns the captured input and clears the buffer.
Automatically stops capturing when called."""
    global _early_input_buffer
    stopCapturingEarlyInput()
    with _buffer_lock:
        value = _early_input_buffer.strip()
        _early_input_buffer = ""
    return value


def hasEarlyInput():
    """Check if there is any early input available without consuming it."""
    with _buffer_lock:
        return bool(_early_input_buffer.strip())


def seedEarlyInput(text):
    """Seed the early input buffer with text that will appear pre-filled
in the prompt input when the REPL renders. Does not auto-submit."""
    global _early_input_buffer
    with _buffer_lock:
        _early_input_buffer = text


def isCapturingEarlyInput():
    """Check if early input capture is currently active."""
    return _is_capturing


start_capturing_early_input = startCapturingEarlyInput
process_chunk = processChunk
stop_capturing_early_input = stopCapturingEarlyInput
consume_early_input = consumeEarlyInput
has_early_input = hasEarlyInput
seed_early_input = seedEarlyInput
is_capturing_early_input = isCapturingEarlyInput

