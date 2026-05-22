"""Mailbox — mirrors src/utils/mailbox.ts"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Literal, Optional

from .signal import Signal

MessageSource = Literal["user", "teammate", "system", "tick", "task"]


@dataclass
class MailboxMessage:
    id: str
    source: MessageSource
    content: str
    from_: Optional[str] = None
    color: Optional[str] = None
    timestamp: str = field(default_factory=lambda: str(time.time()))


class Mailbox:
    """Thread-safe message queue with signal-based notifications.

    Mirrors Mailbox from mailbox.ts.
    """

    def __init__(self) -> None:
        self._queue: List[MailboxMessage] = []
        self._waiters: List[tuple[Callable[[MailboxMessage], bool], asyncio.Future]] = []
        self._changed = Signal()
        self._revision = 0

    @property
    def length(self) -> int:
        return len(self._queue)

    @property
    def revision(self) -> int:
        return self._revision

    def send(self, msg: MailboxMessage) -> None:
        """Deliver a message, waking a waiter if one is ready for it."""
        self._revision += 1
        for i, (predicate, future) in enumerate(self._waiters):
            if predicate(msg):
                self._waiters.pop(i)
                if not future.done():
                    future.set_result(msg)
                self._notify()
                return
        self._queue.append(msg)
        self._notify()

    def poll(self, predicate: Optional[Callable[[MailboxMessage], bool]] = None) -> Optional[MailboxMessage]:
        """Non-blocking: return and remove the first matching message, or None."""
        fn = predicate or (lambda _: True)
        for i, msg in enumerate(self._queue):
            if fn(msg):
                return self._queue.pop(i)
        return None

    async def receive(self, predicate: Optional[Callable[[MailboxMessage], bool]] = None) -> MailboxMessage:
        """Blocking: wait until a matching message arrives."""
        fn = predicate or (lambda _: True)
        msg = self.poll(fn)
        if msg is not None:
            return msg
        loop = asyncio.get_event_loop()
        future: asyncio.Future[MailboxMessage] = loop.create_future()
        self._waiters.append((fn, future))
        return await future

    def subscribe(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to mailbox change notifications."""
        return self._changed.subscribe(listener)

    def _notify(self) -> None:
        self._changed.emit()
