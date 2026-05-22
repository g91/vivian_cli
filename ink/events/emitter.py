"""Port of src/ink/events/emitter.ts."""
from __future__ import annotations

from typing import Any, Callable


class Emitter:
    __slots__ = ("_listeners",)

    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable[..., Any]]] = {}

    def on(self, event: str, listener: Callable[..., Any]) -> None:
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(listener)

    def off(self, event: str, listener: Callable[..., Any]) -> None:
        if event in self._listeners:
            try:
                self._listeners[event].remove(listener)
            except ValueError:
                pass

    def emit(self, event: str, *args: Any) -> None:
        for listener in self._listeners.get(event, []):
            listener(*args)
