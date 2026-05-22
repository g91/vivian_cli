"""Idle timeout manager — mirrors src/utils/idleTimeout.ts"""
from __future__ import annotations

import asyncio
import os
from typing import Callable, TypedDict

_DEFAULT_STOP_DELAY_MS = 10_000  # 10 seconds


class IdleTimeoutHandle(TypedDict):
    start: Callable[[], None]
    stop: Callable[[], None]


def create_idle_timeout_manager(
    is_idle: Callable[[], bool],
) -> IdleTimeoutHandle:
    """Create an idle timeout manager that calls sys.exit when idle.

    Controlled by ``vivian_CODE_EXIT_AFTER_STOP_DELAY`` env var (ms).
    Returns a dict with ``start()`` and ``stop()`` callables.
    Mirrors createIdleTimeoutManager() from idleTimeout.ts.
    """
    raw = os.environ.get("vivian_CODE_EXIT_AFTER_STOP_DELAY", "").strip()
    if not raw:
        return IdleTimeoutHandle(start=lambda: None, stop=lambda: None)

    try:
        delay_ms = int(raw)
    except ValueError:
        return IdleTimeoutHandle(start=lambda: None, stop=lambda: None)

    handle: list[asyncio.TimerHandle | None] = [None]

    def _fire() -> None:
        if is_idle():
            import sys
            sys.exit(0)
        # Not idle yet — rearm
        _schedule()

    def _schedule() -> None:
        loop = asyncio.get_event_loop()
        handle[0] = loop.call_later(delay_ms / 1000, _fire)

    def _start() -> None:
        if handle[0] is None:
            _schedule()

    def _stop() -> None:
        if handle[0] is not None:
            handle[0].cancel()
            handle[0] = None

    return IdleTimeoutHandle(start=_start, stop=_stop)
