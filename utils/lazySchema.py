"""Lazy schema/value factory — mirrors src/utils/lazySchema.ts"""
from __future__ import annotations

from typing import Callable, Generic, Optional, TypeVar

T = TypeVar("T")


def lazy_schema(factory: Callable[[], T]) -> Callable[[], T]:
    """Returns a memoized factory function that constructs the value on first call.
    Used to defer expensive schema/object construction from import time to first access.

    Mirrors lazySchema() from lazySchema.ts.
    """
    cached: list = []  # use list to allow mutation in closure

    def get() -> T:
        if not cached:
            cached.append(factory())
        return cached[0]

    return get
