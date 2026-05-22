"""Buffered file writer — mirrors src/utils/bufferedWriter.ts"""
from __future__ import annotations
import asyncio
from typing import Optional

class BufferedWriter:
    """Buffers writes and flushes periodically."""
    def __init__(self, path: str, *, flush_interval_ms: int = 100):
        self.path = path
        self._buffer: list[str] = []
        self._flush_interval = flush_interval_ms / 1000

    async def write(self, data: str) -> None:
        self._buffer.append(data)

    async def flush(self) -> None:
        if not self._buffer:
            return
        content = "".join(self._buffer)
        self._buffer.clear()
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(content)

    async def close(self) -> None:
        await self.flush()

def create_buffered_writer(path: str, *, flush_interval_ms: int = 100) -> BufferedWriter:
    return BufferedWriter(path, flush_interval_ms=flush_interval_ms)
