"""Port of src/hooks/useDeferredHookMessages.ts."""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional


async def useDeferredHookMessages(
    pendingHookMessages: Optional[Awaitable[list[dict]]],
    setMessages: Callable[[Callable[[list[Any]], list[Any]]], None],
) -> Callable[[], Awaitable[None]]:
    resolved = pendingHookMessages is None

    async def flush() -> None:
        nonlocal resolved, pendingHookMessages
        if resolved or pendingHookMessages is None:
            return
        msgs = await pendingHookMessages
        if resolved:
            return
        resolved = True
        pendingHookMessages = None
        if msgs:
            setMessages(lambda prev: [*msgs, *prev])

    if pendingHookMessages is not None:
        await flush()
    return flush
