"""File read cache — mirrors src/utils/fileReadCache.ts"""
from __future__ import annotations
import asyncio
from typing import Optional

_cache: dict[str, tuple[str, float]] = {}

async def read_file_cached(path: str, *, ttl_s: float = 5.0) -> str:
    import time, os
    now = time.monotonic()
    if path in _cache:
        content, ts = _cache[path]
        if now - ts < ttl_s:
            return content
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    _cache[path] = (content, now)
    return content
