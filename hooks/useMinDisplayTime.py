"""Port of src/hooks/useMinDisplayTime.ts."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar('T')


@dataclass
class _MinDisplayState(Generic[T]):
    displayed: T
    last_shown_at: float


def useMinDisplayTime(value: T, minMs: int, state: _MinDisplayState[T] | None = None) -> tuple[T, _MinDisplayState[T]]:
    now = time.time() * 1000
    if state is None:
        return value, _MinDisplayState(displayed=value, last_shown_at=now)

    elapsed = now - state.last_shown_at
    if elapsed >= minMs:
        state.displayed = value
        state.last_shown_at = now
    return state.displayed, state
