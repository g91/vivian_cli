"""Promise.withResolvers polyfill — mirrors src/utils/withResolvers.ts"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class PromiseWithResolvers(Generic[T]):
    """Equivalent of PromiseWithResolvers from ES2024 / Promise.withResolvers()."""
    future: "asyncio.Future[T]"
    resolve: Callable[[T], None]
    reject: Callable[[BaseException], None]


def with_resolvers() -> PromiseWithResolvers:
    """Create a Future together with its resolve/reject callbacks.

    Mirrors Promise.withResolvers() from withResolvers.ts.

    Usage::

        wr = with_resolvers()
        wr.resolve(42)
        result = await wr.future  # → 42
    """
    loop = asyncio.get_event_loop()
    future: asyncio.Future = loop.create_future()

    def resolve(value) -> None:
        if not future.done():
            future.set_result(value)

    def reject(exc: BaseException) -> None:
        if not future.done():
            future.set_exception(exc)

    return PromiseWithResolvers(future=future, resolve=resolve, reject=reject)
