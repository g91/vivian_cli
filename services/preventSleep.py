"""Prevent sleep service — mirrors src/services/preventSleep.ts."""
from __future__ import annotations

import subprocess
import sys
import threading
from typing import Optional

from ..utils.cleanupRegistry import register_cleanup
from ..utils.debug import logForDebugging

CAFFEINATE_TIMEOUT_SECONDS = 300  # 5 minutes
RESTART_INTERVAL_MS = 4 * 60 * 1000  # 4 minutes

_caffeinate_process: Optional[subprocess.Popen] = None
_restart_timer: Optional[threading.Timer] = None
_ref_count = 0
_lock = threading.Lock()
_cleanup_registered = False


def _spawn_caffeinate() -> None:
    global _caffeinate_process, _cleanup_registered
    if sys.platform != "darwin":
        return
    if _caffeinate_process is not None:
        return

    if not _cleanup_registered:
        _cleanup_registered = True

        async def _cleanup() -> None:
            forceStopPreventSleep()

        register_cleanup(_cleanup)

    try:
        _caffeinate_process = subprocess.Popen(
            ["caffeinate", "-i", "-t", str(CAFFEINATE_TIMEOUT_SECONDS)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logForDebugging("Started caffeinate to prevent sleep")
    except Exception:
        _caffeinate_process = None


def _stop_caffeinate() -> None:
    global _caffeinate_process
    if _caffeinate_process is not None:
        try:
            _caffeinate_process.kill()
            logForDebugging("Stopped caffeinate, allowing sleep")
        except Exception:
            pass
        _caffeinate_process = None


def _start_restart_interval() -> None:
    global _restart_timer
    if _restart_timer is not None:
        return
    _restart_timer = threading.Timer(RESTART_INTERVAL_MS / 1000, _on_restart_interval)
    _restart_timer.daemon = True
    _restart_timer.start()


def _stop_restart_interval() -> None:
    global _restart_timer
    if _restart_timer is not None:
        _restart_timer.cancel()
        _restart_timer = None


def _on_restart_interval() -> None:
    global _restart_timer
    _restart_timer = None
    with _lock:
        if _ref_count > 0:
            logForDebugging("Restarting caffeinate to maintain sleep prevention")
            _stop_caffeinate()
            _spawn_caffeinate()
            _start_restart_interval()


def startPreventSleep() -> None:
    """Increment the reference count and start preventing sleep if needed.

    Mirrors startPreventSleep() from preventSleep.ts.
    """
    global _ref_count
    with _lock:
        _ref_count += 1
        if _ref_count == 1:
            _spawn_caffeinate()
            _start_restart_interval()


def stopPreventSleep() -> None:
    """Decrement the reference count and stop preventing sleep if at zero.

    Mirrors stopPreventSleep() from preventSleep.ts.
    """
    global _ref_count
    with _lock:
        if _ref_count > 0:
            _ref_count -= 1
        if _ref_count == 0:
            _stop_caffeinate()
            _stop_restart_interval()


def forceStopPreventSleep() -> None:
    """Force-stop sleep prevention regardless of reference count.

    Mirrors forceStopPreventSleep() from preventSleep.ts.
    """
    global _ref_count
    with _lock:
        _ref_count = 0
        _stop_caffeinate()
        _stop_restart_interval()


start_prevent_sleep = startPreventSleep
stop_prevent_sleep = stopPreventSleep
force_stop_prevent_sleep = forceStopPreventSleep
