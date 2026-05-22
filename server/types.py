"""Server types — mirrors src/server/types.ts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional


# ---------------------------------------------------------------------------
# ConnectResponse (from connectResponseSchema)
# ---------------------------------------------------------------------------

@dataclass
class ConnectResponse:
    session_id: str
    ws_url: str
    work_dir: Optional[str] = None


def parse_connect_response(d: dict) -> ConnectResponse:
    """Parse the JSON body from POST /sessions into a ConnectResponse."""
    if not isinstance(d, dict):
        raise TypeError("response must be an object")

    session_id = d.get("session_id")
    ws_url = d.get("ws_url")
    work_dir = d.get("work_dir")

    if not isinstance(session_id, str) or not session_id:
        raise ValueError("session_id must be a non-empty string")
    if not isinstance(ws_url, str) or not ws_url:
        raise ValueError("ws_url must be a non-empty string")
    if work_dir is not None and not isinstance(work_dir, str):
        raise ValueError("work_dir must be a string when present")

    return ConnectResponse(
        session_id=session_id,
        ws_url=ws_url,
        work_dir=work_dir,
    )


# ---------------------------------------------------------------------------
# ServerConfig
# ---------------------------------------------------------------------------

@dataclass
class ServerConfig:
    port: int
    host: str
    auth_token: str
    unix: Optional[str] = None
    idle_timeout_ms: Optional[int] = None
    """Idle timeout for detached sessions (ms). 0 = never expire."""
    max_sessions: Optional[int] = None
    """Maximum number of concurrent sessions."""
    workspace: Optional[str] = None
    """Default workspace directory for sessions that don't specify cwd."""


# ---------------------------------------------------------------------------
# SessionState
# ---------------------------------------------------------------------------

SessionState = Literal["starting", "running", "detached", "stopping", "stopped"]


# ---------------------------------------------------------------------------
# SessionInfo
# ---------------------------------------------------------------------------

@dataclass
class SessionInfo:
    id: str
    status: str  # SessionState
    created_at: float  # timestamp (ms since epoch)
    work_dir: str
    process: Optional[Any] = None  # subprocess handle (not serialisable)
    session_key: Optional[str] = None


# ---------------------------------------------------------------------------
# SessionIndexEntry / SessionIndex
# ---------------------------------------------------------------------------

@dataclass
class SessionIndexEntry:
    """Stable session key → session metadata.

    Persisted to ~/.vivian/server-sessions.json so sessions can be resumed
    across server restarts.
    """
    session_id: str
    """Server-assigned session ID."""
    transcript_session_id: str
    """The vivian transcript session ID for --resume."""
    cwd: str
    permission_mode: Optional[str] = None
    created_at: float = 0.0
    last_active_at: float = 0.0


# Record[str, SessionIndexEntry]
SessionIndex = dict  # str -> SessionIndexEntry
