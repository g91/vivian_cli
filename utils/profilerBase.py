"""Profiler base — mirrors src/utils/profilerBase.ts"""
from __future__ import annotations
import time
from typing import Optional

class ProfilerBase:
    def __init__(self) -> None:
        self._marks: dict[str, float] = {}

    def mark(self, label: str) -> None:
        self._marks[label] = time.monotonic()

    def measure(self, start: str, end: str) -> Optional[float]:
        s = self._marks.get(start)
        e = self._marks.get(end)
        if s is None or e is None:
            return None
        return (e - s) * 1000
