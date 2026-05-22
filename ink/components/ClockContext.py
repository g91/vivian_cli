"""Port of src/ink/components/ClockContext.tsx."""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Callable, Iterator

from ..constants import FRAME_INTERVAL_MS


class SharedClock:
    __slots__ = (
        "_subscribers",
        "_lock",
        "_tick_interval_ms",
        "_start_time_ms",
        "_tick_time_ms",
        "_stop_event",
        "_thread",
    )

    def __init__(self) -> None:
        self._subscribers: list[tuple[Callable[[], None], bool]] = []
        self._lock = threading.Lock()
        self._tick_interval_ms = FRAME_INTERVAL_MS
        self._start_time_ms = 0
        self._tick_time_ms = 0
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def now(self) -> int:
        if self._start_time_ms == 0:
            self._start_time_ms = int(time.time() * 1000)
        if self._thread is not None and self._tick_time_ms:
            return self._tick_time_ms
        return int(time.time() * 1000) - self._start_time_ms

    def subscribe(self, callback: Callable[[], None], keepAlive: bool = False) -> Callable[[], None]:
        with self._lock:
            self._subscribers.append((callback, keepAlive))
        self._update_thread()

        def unsubscribe() -> None:
            with self._lock:
                self._subscribers = [entry for entry in self._subscribers if entry[0] is not callback]
            self._update_thread()

        return unsubscribe

    def tick(self) -> None:
        if self._start_time_ms == 0:
            self._start_time_ms = int(time.time() * 1000)
        self._tick_time_ms = int(time.time() * 1000) - self._start_time_ms
        with self._lock:
            callbacks = [callback for callback, _ in self._subscribers]
        for callback in callbacks:
            callback()

    def setTickInterval(self, ms: int) -> None:
        if ms == self._tick_interval_ms:
            return
        self._tick_interval_ms = ms
        self._update_thread()

    def _update_thread(self) -> None:
        with self._lock:
            any_keep_alive = any(keep_alive for _, keep_alive in self._subscribers)

        if any_keep_alive:
            if self._thread is None or not self._thread.is_alive():
                self._stop_event = threading.Event()
                self._thread = threading.Thread(target=self._run, daemon=True)
                self._thread.start()
            return

        if self._thread is not None:
            self._stop_event.set()
            self._thread = None

    def _run(self) -> None:
        while not self._stop_event.wait(self._tick_interval_ms / 1000):
            self.tick()


_CLOCK_CONTEXT: ContextVar[SharedClock | None] = ContextVar("ink_clock_context", default=None)


def getClockContext() -> SharedClock | None:
    return _CLOCK_CONTEXT.get()


def setClockContext(clock: SharedClock | None) -> Token[SharedClock | None]:
    return _CLOCK_CONTEXT.set(clock)


def resetClockContext(token: Token[SharedClock | None]) -> None:
    _CLOCK_CONTEXT.reset(token)


@contextmanager
def ClockProvider(clock: SharedClock | None = None) -> Iterator[SharedClock]:
    provided = clock or SharedClock()
    token = setClockContext(provided)
    try:
        yield provided
    finally:
        resetClockContext(token)


ClockContext = SharedClock
