"""Async generator utilities — mirrors src/utils/generators.ts"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Optional, TypeVar

A = TypeVar("A")
T = TypeVar("T")

_NO_VALUE = object()


async def lastX(as_: AsyncGenerator[A, None]) -> A:
    """Return the last value from an async generator.

    Raises Exception if the generator produces no items.
    """
    last_value: Any = _NO_VALUE
    async for a in as_:
        last_value = a
    if last_value is _NO_VALUE:
        raise Exception("No items in generator")
    return last_value


async def returnValue(as_: AsyncGenerator[Any, A]) -> A:
    """Drain an async generator and return its final return value."""
    try:
        await as_.__anext__()
    except StopAsyncIteration as exc:
        return exc.value
    raise Exception("Generator did not finish")


async def toArray(generator: AsyncGenerator[A, None]) -> list[A]:
    """Collect all values from an async generator into a list."""
    result: list[A] = []
    async for a in generator:
        result.append(a)
    return result


async def fromArray(values: list[T]) -> AsyncGenerator[T, None]:
    """Yield each value from a list as an async generator."""
    for value in values:
        yield value


async def all_generators(
    generators: list[AsyncGenerator[A, None]],
    concurrency_cap: int = 0,
) -> AsyncGenerator[A, None]:
    """Run generators concurrently up to a cap, yielding values as they arrive."""
    if not generators:
        return
    cap = concurrency_cap if concurrency_cap > 0 else len(generators)
    waiting = list(generators)
    active: set[asyncio.Task] = set()

    async def _run_one(gen: AsyncGenerator[A, None]) -> Optional[A]:
        try:
            return await gen.__anext__()
        except StopAsyncIteration:
            return None

    while len(active) < cap and waiting:
        g = waiting.pop(0)
        active.add(asyncio.create_task(_run_one(g)))

    while active:
        done, active = await asyncio.wait(active, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            try:
                value = task.result()
            except Exception:
                continue
            if value is not None:
                yield value
            if waiting:
                g = waiting.pop(0)
                active.add(asyncio.create_task(_run_one(g)))
