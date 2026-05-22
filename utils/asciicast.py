"""Minimal asciicast recording helpers."""
from __future__ import annotations

import time
from typing import Any


class AsciicastRecorder:
    def __init__(
        self,
        *,
        width: int = 80,
        height: int = 24,
        shell: str = '',
        term: str = '',
        start_time: float | None = None,
    ) -> None:
        self._started_at = start_time if start_time is not None else time.perf_counter()
        self._header = {
            'version': 2,
            'width': width,
            'height': height,
            'timestamp': int(time.time()),
            'env': {
                'SHELL': shell,
                'TERM': term,
            },
        }
        self._events: list[list[Any]] = []

    def record(self, data: str, *, output: bool = True) -> None:
        event_type = 'o' if output else 'i'
        elapsed = max(0.0, time.perf_counter() - self._started_at)
        self._events.append([elapsed, event_type, data])

    def resize(self, width: int, height: int) -> None:
        elapsed = max(0.0, time.perf_counter() - self._started_at)
        self._events.append([elapsed, 'r', f'{width}x{height}'])

    def to_cast(self) -> dict[str, Any]:
        return {
            **self._header,
            'events': list(self._events),
        }


asciicast_recorder = AsciicastRecorder
