"""Remote session — mirrors src/hooks/useRemoteSession.ts."""
from __future__ import annotations

async def useRemoteSession() -> dict:
    """Remote session management."""
    return {"connected": False}

use_remote_session = useRemoteSession
