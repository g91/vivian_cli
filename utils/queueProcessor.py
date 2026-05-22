"""Queue processor — mirrors src/utils/queueProcessor.ts"""
from __future__ import annotations
import asyncio
from typing import Any, Callable


class QueueProcessor:
    def __init__(self, handler: Callable) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()
        self._handler = handler

    async def enqueue(self, item: Any) -> None:
        await self._queue.put(item)

    async def process_all(self) -> None:
        while not self._queue.empty():
            item = await self._queue.get()
            await self._handler(item)
            self._queue.task_done()
