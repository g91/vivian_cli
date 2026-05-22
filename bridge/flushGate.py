"""Port of src/bridge/flushGate.ts

State machine for gating message writes during an initial flush.

Lifecycle:
  start() → enqueue() returns True, items are queued
  end()   → returns queued items for draining, enqueue() returns False
  drop()  → discards queued items (permanent transport close)
  deactivate() → clears active flag without dropping items
"""
from __future__ import annotations

from typing import Generic, List, TypeVar

T = TypeVar("T")


class FlushGate(Generic[T]):
    """Generic flush gate for any message type T."""

    def __init__(self) -> None:
        self._active = False
        self._pending: List[T] = []

    @property
    def active(self) -> bool:
        return self._active

    @property
    def pendingCount(self) -> int:
        return len(self._pending)

    def start(self) -> None:
        """Mark flush as in-progress. enqueue() will start queuing items."""
        self._active = True

    def end(self) -> List[T]:
        """End the flush and return any queued items for draining."""
        self._active = False
        items = list(self._pending)
        self._pending.clear()
        return items

    def enqueue(self, *items: T) -> bool:
        """Queue items if flush active, return True. Otherwise return False."""
        if not self._active:
            return False
        self._pending.extend(items)
        return True

    def drop(self) -> int:
        """Discard all queued items (permanent transport close). Returns count dropped."""
        self._active = False
        count = len(self._pending)
        self._pending.clear()
        return count

    def deactivate(self) -> None:
        """Clear active flag without dropping items (transport replacement)."""
        self._active = False
