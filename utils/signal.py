"""Signal / event emitter — mirrors src/utils/signal.ts"""
from __future__ import annotations

from typing import Callable, Generic, List, Set, TypeVar

_Listener = Callable[..., None]


class Signal:
    """Typed pub/sub signal. Mirrors Signal<Args> from signal.ts."""

    def __init__(self) -> None:
        self._listeners: set[_Listener] = set()

    def subscribe(self, listener: _Listener) -> Callable[[], None]:
        """Subscribe to signal. Returns an unsubscribe function."""
        self._listeners.add(listener)

        def unsubscribe() -> None:
            self._listeners.discard(listener)

        return unsubscribe

    def emit(self, *args, **kwargs) -> None:
        """Emit signal to all listeners."""
        for listener in list(self._listeners):
            listener(*args, **kwargs)

    def clear(self) -> None:
        """Remove all listeners."""
        self._listeners.clear()


def create_signal() -> Signal:
    """Create a new Signal instance. Mirrors createSignal() from signal.ts."""
    return Signal()
