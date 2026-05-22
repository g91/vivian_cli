"""Notify after timeout — mirrors src/hooks/useNotifyAfterTimeout.ts."""
from __future__ import annotations

async def useNotifyAfterTimeout(ms: int, message: str = "") -> dict:
    """Notify after delay."""
    return {"ms": ms, "message": message}

use_notify_after_timeout = useNotifyAfterTimeout
