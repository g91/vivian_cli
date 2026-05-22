"""Circular buffer — mirrors src/utils/CircularBuffer.ts"""
from __future__ import annotations

from typing import Generic, List, TypeVar

T = TypeVar("T")


class CircularBuffer(Generic[T]):
    """Fixed-size circular buffer that evicts the oldest item when full."""

    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._buffer: list = [None] * capacity
        self._head = 0
        self._size = 0

    def add(self, item: T) -> None:
        """Add an item, evicting the oldest if the buffer is full."""
        self._buffer[self._head] = item
        self._head = (self._head + 1) % self._capacity
        if self._size < self._capacity:
            self._size += 1

    def add_all(self, items: List[T]) -> None:
        """Add multiple items at once."""
        for item in items:
            self.add(item)

    def get_recent(self, count: int) -> List[T]:
        """Return the most recent `count` items (fewer if buffer is smaller)."""
        available = min(count, self._size)
        if available == 0:
            return []
        start = 0 if self._size < self._capacity else self._head
        result = []
        for i in range(available):
            idx = (start + self._size - available + i) % self._capacity
            result.append(self._buffer[idx])
        return result

    def to_array(self) -> List[T]:
        """Return all items in order from oldest to newest."""
        if self._size == 0:
            return []
        start = 0 if self._size < self._capacity else self._head
        result = []
        for i in range(self._size):
            idx = (start + i) % self._capacity
            result.append(self._buffer[idx])
        return result

    def clear(self) -> None:
        """Remove all items."""
        self._buffer = [None] * self._capacity
        self._head = 0
        self._size = 0

    def length(self) -> int:
        """Return the current number of items."""
        return self._size
