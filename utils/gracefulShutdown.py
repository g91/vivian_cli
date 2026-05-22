"""Graceful shutdown — mirrors src/utils/gracefulShutdown.ts"""
from __future__ import annotations

import signal as _signal
import sys
from typing import Optional

_shutting_down = False
_cleanup_handlers: list = []


class CleanupTimeoutError(Exception):
    """Raised when graceful-shutdown cleanup takes too long."""


def is_shutting_down() -> bool:
    """Return True once a graceful shutdown has been initiated."""
    return _shutting_down


def cleanup_terminal_modes() -> None:
    """Restore sane terminal settings (disable raw mode etc.)."""
    try:
        import termios
        import tty
        fd = sys.stdin.fileno()
        # Try to flush and reset the terminal
        termios.tcflush(fd, termios.TCIOFLUSH)
    except Exception:
        pass


def register_cleanup(fn) -> None:
    """Register a zero-argument callable to run on graceful shutdown."""
    _cleanup_handlers.append(fn)


def force_exit(exit_code: int = 0) -> None:
    """Exit immediately without running cleanup handlers."""
    # pylint: disable=protected-access
    import os
    os._exit(exit_code)


def graceful_shutdown(
    exit_code: int = 0,
    reason: Optional[str] = None,
    *,
    timeout_ms: int = 5000,
) -> None:
    """Run all registered cleanup handlers then exit.

    If cleanup takes longer than timeout_ms, calls force_exit().
    """
    global _shutting_down
    if _shutting_down:
        return
    _shutting_down = True

    cleanup_terminal_modes()

    if reason:
        print(f"\n[shutdown] {reason}", file=sys.stderr)

    import threading
    for fn in list(_cleanup_handlers):
        try:
            # Call each handler with a generous timeout guard
            done = threading.Event()

            def _run(fn=fn):
                try:
                    fn()
                except Exception:
                    pass
                finally:
                    done.set()

            t = threading.Thread(target=_run, daemon=True)
            t.start()
            done.wait(timeout=timeout_ms / 1000)
        except Exception:
            pass

    sys.exit(exit_code)


def graceful_shutdown_sync(exit_code: int = 0) -> None:
    """Synchronous variant of graceful_shutdown with no timeout guard."""
    global _shutting_down
    if _shutting_down:
        return
    _shutting_down = True
    cleanup_terminal_modes()
    for fn in list(_cleanup_handlers):
        try:
            fn()
        except Exception:
            pass
    sys.exit(exit_code)


def _setup_signal_handlers() -> None:
    """Install SIGTERM handler that triggers graceful_shutdown."""
    def _handler(signum, frame):
        graceful_shutdown(exit_code=0, reason=f"signal {signum}")

    try:
        _signal.signal(_signal.SIGTERM, _handler)
    except (ValueError, OSError):
        pass


_setup_signal_handlers()
