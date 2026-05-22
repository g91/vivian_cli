"""Sequential async execution — mirrors src/utils/sequential.ts"""
from __future__ import annotations

import asyncio
from collections import deque
from typing import Any, Callable, Coroutine, Deque, Generic, Optional, TypeVar

R = TypeVar("R")


def sequential(fn: Callable[..., Coroutine[Any, Any, R]]) -> Callable[..., Coroutine[Any, Any, R]]:
    """Wrap an async function so that concurrent calls execute one at a time,
    in the order they were received.

    Equivalent to TypeScript's sequential() from sequential.ts.
    """
    queue: Deque[tuple[tuple, dict, asyncio.Future]] = deque()
    processing = False

    async def process_queue() -> None:
        nonlocal processing
        if processing:
            return
        processing = True
        try:
            while queue:
                args, kwargs, future = queue.popleft()
                try:
                    result = await fn(*args, **kwargs)
                    future.set_result(result)
                except Exception as e:
                    future.set_exception(e)
        finally:
            processing = False
        # Check if new items were added while processing
        if queue:
            asyncio.ensure_future(process_queue())

    async def wrapper(*args: Any, **kwargs: Any) -> R:
        loop = asyncio.get_event_loop()
        future: asyncio.Future[R] = loop.create_future()
        queue.append((args, kwargs, future))
        asyncio.ensure_future(process_queue())
        return await future

    return wrapper
