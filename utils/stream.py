"""Async stream queue — mirrors src/utils/stream.ts"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator, Callable, Generic, Optional, TypeVar

T = TypeVar("T")


class Stream(Generic[T]):
    """Async queue that implements AsyncIterator.
    Mirrors Stream<T> from stream.ts.

    Usage::

        stream = Stream()
        stream.enqueue("hello")
        stream.enqueue("world")
        stream.done()
        async for item in stream:
            print(item)
    """

    def __init__(self, returned: Optional[Callable[[], None]] = None) -> None:
        self._queue: asyncio.Queue[Optional[T]] = asyncio.Queue()
        self._done = False
        self._error: Optional[BaseException] = None
        self._started = False
        self._returned = returned

    def __aiter__(self) -> "Stream[T]":
        if self._started:
            raise RuntimeError("Stream can only be iterated once")
        self._started = True
        return self

    async def __anext__(self) -> T:
        if self._error is not None:
            raise self._error
        item = await self._queue.get()
        if item is _SENTINEL:
            if self._error is not None:
                raise self._error
            raise StopAsyncIteration
        return item  # type: ignore[return-value]

    def enqueue(self, value: T) -> None:
        """Push a value into the stream."""
        if not self._done:
            self._queue.put_nowait(value)

    def done(self) -> None:
        """Signal end of stream."""
        if not self._done:
            self._done = True
            self._queue.put_nowait(_SENTINEL)  # type: ignore[arg-type]

    def error(self, exc: BaseException) -> None:
        """Signal stream error."""
        self._error = exc
        if not self._done:
            self._done = True
            self._queue.put_nowait(_SENTINEL)  # type: ignore[arg-type]

    def close(self) -> None:
        """Alias for done(); calls returned callback if set."""
        if self._returned:
            self._returned()
        self.done()


class _SentinelType:
    pass


_SENTINEL = _SentinelType()
