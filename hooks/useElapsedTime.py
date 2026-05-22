"""Port of src/hooks/useElapsedTime.ts."""
from __future__ import annotations

import time

from ..utils.format import format_duration


def useElapsedTime(
    startTime: int,
    isRunning: bool,
    ms: int = 1000,
    pausedMs: int = 0,
    endTime: int | None = None,
) -> str:
    del isRunning, ms
    now = endTime if endTime is not None else int(time.time() * 1000)
    duration = max(0, now - startTime - pausedMs)
    return format_duration(duration)
