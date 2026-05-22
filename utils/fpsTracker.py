"""FPS tracker for UI rendering — mirrors src/utils/fpsTracker.ts"""
from __future__ import annotations
import time

class FpsTracker:
    def __init__(self) -> None:
        self._frame_times: list[float] = []

    def record_frame(self) -> None:
        self._frame_times.append(time.monotonic())
        if len(self._frame_times) > 60:
            self._frame_times.pop(0)

    def get_fps(self) -> float:
        if len(self._frame_times) < 2:
            return 0.0
        elapsed = self._frame_times[-1] - self._frame_times[0]
        return len(self._frame_times) / elapsed if elapsed > 0 else 0.0
