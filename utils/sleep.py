"""Sleep / timeout utilities — mirrors src/utils/sleep.ts"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Optional, TypeVar

T = TypeVar("T")


async def sleep(
    ms: float,
    *,
    throw_on_cancel: bool = False,
) -> None:
    """Sleep for `ms` milliseconds. Cancellation-aware: if the task is
    cancelled, behaves according to `throw_on_cancel`.

    Note: Python uses asyncio cancellation rather than AbortSignal.
    """
    try:
        await asyncio.sleep(ms / 1000)
    except asyncio.CancelledError:
        if throw_on_cancel:
            raise
        # Silently resolve like the JS version with throwOnAbort=false


async def with_timeout(
    coro: Awaitable[T],
    ms: float,
    message: str,
) -> T:
    """Race a coroutine against a timeout. Raises TimeoutError(message)
    if the coroutine doesn't complete within `ms` milliseconds.
    """
    try:
        return await asyncio.wait_for(asyncio.ensure_future(coro), timeout=ms / 1000)
    except asyncio.TimeoutError:
        raise TimeoutError(message)
