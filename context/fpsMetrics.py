"""FPS metrics context — mirrors src/context/fpsMetrics.tsx."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any, Callable, Iterator, Optional


GetFpsMetricsContext: ContextVar[Optional[Callable[[], Any]]] = ContextVar(
    "GetFpsMetricsContext",
    default=None,
)


@contextmanager
def FpsMetricsProvider(*, getFpsMetrics: Callable[[], Any] | None) -> Iterator[Callable[[], Any] | None]:
    token: Token[Optional[Callable[[], Any]]] = GetFpsMetricsContext.set(getFpsMetrics)
    try:
        yield getFpsMetrics
    finally:
        GetFpsMetricsContext.reset(token)


def useFpsMetrics() -> Any:
    getter = GetFpsMetricsContext.get()
    if getter is None:
        return None
    return getter()


__all__ = [
    "FpsMetricsProvider",
    "GetFpsMetricsContext",
    "useFpsMetrics",
]