"""Structured I/O — mirrors src/cli/structuredIO.ts.

Reads newline-delimited JSON messages from stdin and writes them to stdout,
providing a control-channel protocol for SDK hosts that drive the CLI
programmatically.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any, AsyncIterator, Callable, Optional

from .ndjson import ndjson_safe_stringify

logger = logging.getLogger(__name__)


class StructuredIO:
    """Bidirectional NDJSON protocol over stdin/stdout.

    SDK hosts write control requests as NDJSON to stdin; the CLI writes
    assistant + tool events back to stdout.  The ``read_messages`` async
    generator yields parsed dicts for each complete line.
    """

    def __init__(
        self,
        on_message: Optional[Callable[[dict], Any]] = None,
        replay_user_messages: bool = False,
    ) -> None:
        self._on_message = on_message
        self._replay_user_messages = replay_user_messages
        self._queue: asyncio.Queue[Optional[dict]] = asyncio.Queue()
        self._reader_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Reading

    async def start_reader(self) -> None:
        """Start background task that reads stdin line-by-line."""
        loop = asyncio.get_event_loop()
        self._reader_task = loop.create_task(self._read_stdin())

    async def _read_stdin(self) -> None:
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        loop = asyncio.get_event_loop()
        await loop.connect_read_pipe(lambda: protocol, sys.stdin.buffer)
        while True:
            try:
                line = await reader.readline()
                if not line:
                    await self._queue.put(None)  # EOF sentinel
                    break
                text = line.decode("utf-8", errors="replace").rstrip("\n")
                if not text:
                    continue
                try:
                    msg = json.loads(text)
                except json.JSONDecodeError:
                    logger.debug("StructuredIO: bad JSON line: %r", text)
                    continue
                if self._on_message:
                    self._on_message(msg)
                await self._queue.put(msg)
            except Exception as exc:
                logger.debug("StructuredIO reader error: %s", exc)
                await self._queue.put(None)
                break

    async def read_messages(self) -> AsyncIterator[dict]:
        """Yield parsed control messages from stdin."""
        while True:
            msg = await self._queue.get()
            if msg is None:
                break
            yield msg

    # ------------------------------------------------------------------
    # Writing

    def write(self, msg: Any) -> None:
        """Write *msg* as a single NDJSON line to stdout."""
        line = ndjson_safe_stringify(msg) + "\n"
        sys.stdout.write(line)
        sys.stdout.flush()

    def write_event(self, event_type: str, **payload: Any) -> None:
        """Convenience wrapper — writes ``{type, ...payload}`` to stdout."""
        self.write({"type": event_type, **payload})

    # ------------------------------------------------------------------
    # Lifecycle

    def stop(self) -> None:
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
