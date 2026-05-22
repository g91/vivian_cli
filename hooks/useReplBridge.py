"""REPL bridge — mirrors src/hooks/useReplBridge.ts."""
from __future__ import annotations

async def useReplBridge() -> dict:
    """REPL bridge connection."""
    return {"connected": False}

use_repl_bridge = useReplBridge
