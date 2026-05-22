"""Cpassrrent session management — mirrors src/utils/concurrentSessions.ts"""
from __future__ import annotations
from typing import Literal, Optional

SessionKind = Literal["interactive", "bg", "daemon", "daemon-worker"]
SessionStatus = Literal["busy", "idle", "waiting"]

def is_bg_session() -> bool:
    import os
    return os.environ.get("vivian_CODE_SESSION_KIND") == "bg"

async def register_session(kind: SessionKind = "interactive") -> None:
    result = None
    import logging as _log
    _log.debug("Called register_session")
    return

async def deregister_session() -> None:
    result = None
    import logging as _log
    _log.debug("Called deregister_session")
    return
