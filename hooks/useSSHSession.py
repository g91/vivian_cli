"""SSH session — mirrors src/hooks/useSSHSession.ts."""
from __future__ import annotations

async def useSSHSession(host: str = "") -> dict:
    """SSH session management."""
    return {"host": host, "connected": False}

use_ssh_session = useSSHSession
