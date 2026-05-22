"""Port of src/bridge/replBridgeHandle.ts

Global pointer to the active REPL bridge handle, so callers outside
the React tree (tools, slash commands) can invoke handle methods.
"""
from __future__ import annotations

from typing import Any, Optional

from .sessionIdCompat import toCompatSessionId

_handle: Optional[Any] = None


def setReplBridgeHandle(h: Optional[Any]) -> None:
    global _handle
    _handle = h
    # Publish (or clear) our bridge session ID in the session record.
    try:
        from ..utils.concurrent_sessions import update_session_bridge_id
        import asyncio
        compat_id = getSelfBridgeCompatId()
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(update_session_bridge_id(compat_id))
        except Exception:
            pass
    except Exception:
        pass


def getReplBridgeHandle() -> Optional[Any]:
    return _handle


def getSelfBridgeCompatId() -> Optional[str]:
    """Our own bridge session ID in session_* compat format, or None."""
    h = getReplBridgeHandle()
    if h is None:
        return None
    bridge_session_id = getattr(h, "bridgeSessionId", None)
    if bridge_session_id is None:
        return None
    return toCompatSessionId(bridge_session_id)
