"""Port of src/ink/reconciler.ts."""
from __future__ import annotations

import time
from typing import Any, Callable

from .events.dispatcher import Dispatcher


dispatcher = Dispatcher()

_last_yoga_ms = 0.0
_last_commit_ms = 0.0
_commit_started_at = 0.0
_debug_repaints = False


def isDebugRepaintsEnabled() -> bool:
    return _debug_repaints


def recordYogaMs(ms: float) -> None:
    global _last_yoga_ms
    _last_yoga_ms = ms


def getLastYogaMs() -> float:
    return _last_yoga_ms


def markCommitStart() -> None:
    global _commit_started_at
    _commit_started_at = time.perf_counter()


def markCommitEnd() -> None:
    global _last_commit_ms, _commit_started_at
    if _commit_started_at:
        _last_commit_ms = (time.perf_counter() - _commit_started_at) * 1000
        _commit_started_at = 0.0


def getLastCommitMs() -> float:
    return _last_commit_ms


def resetProfileCounters() -> None:
    global _last_yoga_ms, _last_commit_ms, _commit_started_at
    _last_yoga_ms = 0.0
    _last_commit_ms = 0.0
    _commit_started_at = 0.0


class Reconciler:
    def discreteUpdates(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        markCommitStart()
        try:
            return fn(*args, **kwargs)
        finally:
            markCommitEnd()

    def flushSync(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return self.discreteUpdates(fn, *args, **kwargs)


reconciler = Reconciler()
