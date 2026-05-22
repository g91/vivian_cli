"""Memoization utilities — mirrors src/utils/memoize.ts"""
from __future__ import annotations

import asyncio
import threading
import time
from collections import OrderedDict
from types import SimpleNamespace
from typing import Any, Awaitable, Callable, Optional, TypeVar

from .log import logError
from .slowOperations import jsonStringify

T = TypeVar("T")
K = TypeVar("K")


class _TTLCacheEntry:
    def __init__(self, value: Any, timestamp: float, refreshing: bool = False) -> None:
        self.value = value
        self.timestamp = timestamp
        self.refreshing = refreshing


# ---------------------------------------------------------------------------
# TTL memoize
# ---------------------------------------------------------------------------

def memoize_with_ttl(
    fn: Callable[..., T],
    cache_lifetime_ms: float = 5 * 60 * 1000,
) -> Callable[..., T]:
    """Memoize a sync function with stale-while-refresh cache semantics."""
    cache: dict[str, _TTLCacheEntry] = {}
    lock = threading.Lock()

    def refresh_in_background(key: str, args: tuple[Any, ...], kwargs: dict[str, Any], stale_entry: _TTLCacheEntry) -> None:
        def runner() -> None:
            try:
                new_value = fn(*args, **kwargs)
                with lock:
                    if cache.get(key) is stale_entry:
                        cache[key] = _TTLCacheEntry(new_value, time.time() * 1000)
            except Exception as error:
                logError(error)
                with lock:
                    if cache.get(key) is stale_entry:
                        cache.pop(key, None)

        threading.Thread(target=runner, daemon=True).start()

    def wrapper(*args, **kwargs):
        key = jsonStringify([args, kwargs])
        now = time.time() * 1000
        with lock:
            cached = cache.get(key)
            if cached is None:
                cached_value = None
            else:
                cached_value = cached.value
                if now - cached.timestamp > cache_lifetime_ms and not cached.refreshing:
                    cached.refreshing = True
                    refresh_in_background(key, args, kwargs, cached)
                return cached_value

        result = fn(*args, **kwargs)
        with lock:
            cache[key] = _TTLCacheEntry(result, now)
        return result

    wrapper.cache = SimpleNamespace(clear=lambda: cache.clear())  # type: ignore[attr-defined]
    return wrapper


def memoize_with_ttl_async(
    fn: Callable[..., Awaitable[T]],
    cache_lifetime_ms: float = 5 * 60 * 1000,
) -> Callable[..., Any]:
    """Memoize an async function with stale-while-refresh and cold-miss dedup."""
    cache: dict[str, _TTLCacheEntry] = {}
    in_flight: dict[str, asyncio.Future[T]] = {}

    async def wrapper(*args, **kwargs):
        key = jsonStringify([args, kwargs])
        now = time.time() * 1000
        cached = cache.get(key)

        if cached is None:
            pending = in_flight.get(key)
            if pending is not None:
                return await pending

            loop = asyncio.get_running_loop()
            promise = loop.create_task(fn(*args, **kwargs))
            in_flight[key] = promise
            try:
                result = await promise
                if in_flight.get(key) is promise:
                    cache[key] = _TTLCacheEntry(result, now)
                return result
            finally:
                if in_flight.get(key) is promise:
                    in_flight.pop(key, None)

        if now - cached.timestamp > cache_lifetime_ms and not cached.refreshing:
            cached.refreshing = True
            stale_entry = cached

            async def refresh() -> None:
                try:
                    new_value = await fn(*args, **kwargs)
                    if cache.get(key) is stale_entry:
                        cache[key] = _TTLCacheEntry(new_value, time.time() * 1000)
                except Exception as error:
                    logError(error)
                    if cache.get(key) is stale_entry:
                        cache.pop(key, None)

            asyncio.create_task(refresh())

        return cache[key].value

    wrapper.cache = SimpleNamespace(  # type: ignore[attr-defined]
        clear=lambda: (cache.clear(), in_flight.clear())
    )
    return wrapper


# ---------------------------------------------------------------------------
# LRU memoize
# ---------------------------------------------------------------------------

def memoize_with_lru(
    fn: Callable[..., T],
    cache_fn: Callable[..., Any],
    max_cache_size: int = 100,
) -> Callable[..., T]:
    """Memoize with an LRU eviction strategy and cache management surface."""
    _cache: OrderedDict[Any, T] = OrderedDict()

    def wrapper(*args, **kwargs):
        key = cache_fn(*args, **kwargs)
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
        result = fn(*args, **kwargs)
        _cache[key] = result
        _cache.move_to_end(key)
        if len(_cache) > max_cache_size:
            _cache.popitem(last=False)
        return result

    wrapper.cache = SimpleNamespace(  # type: ignore[attr-defined]
        clear=lambda: _cache.clear(),
        size=lambda: len(_cache),
        delete=lambda key: _cache.pop(key, None) is not None,
        get=lambda key: _cache.get(key),
        has=lambda key: key in _cache,
    )
    return wrapper


memoizeWithTTL = memoize_with_ttl
memoizeWithTTLAsync = memoize_with_ttl_async
memoizeWithLRU = memoize_with_lru
