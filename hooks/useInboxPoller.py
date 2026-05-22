"""Inbox poller — mirrors src/hooks/useInboxPoller.ts."""
from __future__ import annotations

async def useInboxPoller(interval: int = 5000) -> dict:
    """Poll for inbox updates."""
    return {"interval": interval, "polling": False}

use_inbox_poller = useInboxPoller
