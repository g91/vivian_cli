"""Port of src/ink/events/event.ts."""
from __future__ import annotations


class Event:
    __slots__ = ("type", "target", "currentTarget", "_propagationStopped", "_immediatePropagationStopped")

    def __init__(self, type: str) -> None:
        self.type = type
        self.target: object | None = None
        self.currentTarget: object | None = None
        self._propagationStopped = False
        self._immediatePropagationStopped = False

    def stopPropagation(self) -> None:
        self._propagationStopped = True

    def stopImmediatePropagation(self) -> None:
        self._immediatePropagationStopped = True
        self._propagationStopped = True

    def didStopPropagation(self) -> bool:
        return self._propagationStopped

    def didStopImmediatePropagation(self) -> bool:
        return self._immediatePropagationStopped
