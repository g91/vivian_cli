"""Global cleanup registry — mirrors src/utils/cleanupRegistry.ts"""
from __future__ import annotations

import asyncio
from typing import Callable, Coroutine

_cleanup_functions: set[Callable[[], Coroutine]] = set()


def register_cleanup(fn: Callable[[], Coroutine]) -> Callable[[], None]:
    """Register an async cleanup function to run during graceful shutdown.

    Returns an unregister callable.
    """
    _cleanup_functions.add(fn)

    def unregister() -> None:
        _cleanup_functions.discard(fn)

    return unregister


async def run_cleanup_functions() -> None:
    """Run all registered cleanup functions concurrently."""
    await asyncio.gather(*(fn() for fn in list(_cleanup_functions)), return_exceptions=True)
