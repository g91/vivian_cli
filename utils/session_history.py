"""Session history — saves/loads full conversation sessions to disk.

Sessions are stored as JSONL files in ~/.vivian/sessions/.
Each file is named by session_id and contains one JSON object per line.
A manifest file (~/.vivian/sessions/index.json) tracks session metadata
so listing sessions is fast without reading every file.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from ..types import Message

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path.home() / ".vivian" / "sessions"
INDEX_FILE = SESSIONS_DIR / "index.json"
MAX_SESSIONS = 100


@dataclass
class SessionMeta:
    session_id: str
    title: str          # first user message (truncated)
    created_at: float   # unix timestamp
    updated_at: float
    message_count: int
    model: str = ""
    cwd: str = ""


@dataclass
class SessionRecord:
    meta: SessionMeta
    messages: list[dict]  # serialized Message dicts


# ── Internal helpers ────────────────────────────────────────────────────────


def _ensure_dir() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _load_index() -> list[SessionMeta]:
    if not INDEX_FILE.exists():
        return []
    try:
        data = json.loads(INDEX_FILE.read_text())
        return [SessionMeta(**s) for s in data]
    except Exception:
        return []


def _save_index(metas: list[SessionMeta]) -> None:
    _ensure_dir()
    try:
        INDEX_FILE.write_text(json.dumps([asdict(m) for m in metas], indent=2))
    except Exception as e:
        logger.debug("session index save error: %s", e)


def _session_file(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def _msg_to_dict(msg: Message) -> dict:
    d: dict = {"role": msg.role}
    if msg.content:
        d["content"] = msg.content
    if msg.tool_calls:
        d["tool_calls"] = msg.tool_calls
    if msg.tool_call_id:
        d["tool_call_id"] = msg.tool_call_id
    if msg.name:
        d["name"] = msg.name
    return d


def _dict_to_msg(d: dict) -> Message:
    return Message(
        role=d.get("role", "user"),
        content=d.get("content"),
        tool_calls=d.get("tool_calls"),
        tool_call_id=d.get("tool_call_id"),
        name=d.get("name"),
    )


# ── Public API ──────────────────────────────────────────────────────────────


class SessionHistoryManager:
    """Manages persistent conversation sessions."""

    def __init__(self, model: str = "", cwd: str = ""):
        self.session_id: str = str(uuid.uuid4())
        self.model = model
        self.cwd = cwd
        self._created_at: float = time.time()
        self._title: str = ""

    # ── Saving ──────────────────────────────────────────────────────────────

    def save_messages(self, messages: list[Message]) -> None:
        """Persist the full message list for the current session."""
        if not messages:
            return
        _ensure_dir()

        # Derive title from first user message
        if not self._title:
            for m in messages:
                if m.role == "user" and m.content:
                    self._title = m.content[:80].replace("\n", " ")
                    break
        title = self._title or "(no title)"

        # Write session file
        session_file = _session_file(self.session_id)
        try:
            data = {
                "session_id": self.session_id,
                "title": title,
                "created_at": self._created_at,
                "updated_at": time.time(),
                "model": self.model,
                "cwd": self.cwd,
                "messages": [_msg_to_dict(m) for m in messages],
            }
            session_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug("session save error: %s", e)
            return

        # Update index
        metas = _load_index()
        # Replace existing entry or append
        now = time.time()
        meta = SessionMeta(
            session_id=self.session_id,
            title=title,
            created_at=self._created_at,
            updated_at=now,
            message_count=len(messages),
            model=self.model,
            cwd=self.cwd,
        )
        metas = [m for m in metas if m.session_id != self.session_id]
        metas.insert(0, meta)  # newest first
        if len(metas) > MAX_SESSIONS:
            # Prune oldest
            for old in metas[MAX_SESSIONS:]:
                _session_file(old.session_id).unlink(missing_ok=True)
            metas = metas[:MAX_SESSIONS]
        _save_index(metas)

    # ── Loading ──────────────────────────────────────────────────────────────

    @staticmethod
    def list_sessions(limit: int = 20) -> list[SessionMeta]:
        """Return the most recent sessions (newest first)."""
        return _load_index()[:limit]

    @staticmethod
    def load_session(session_id: str) -> Optional[SessionRecord]:
        """Load a session by ID. Returns None if not found."""
        f = _session_file(session_id)
        if not f.exists():
            return None
        try:
            data = json.loads(f.read_text())
            meta = SessionMeta(
                session_id=data["session_id"],
                title=data.get("title", ""),
                created_at=data.get("created_at", 0),
                updated_at=data.get("updated_at", 0),
                message_count=len(data.get("messages", [])),
                model=data.get("model", ""),
                cwd=data.get("cwd", ""),
            )
            messages = [_dict_to_msg(m) for m in data.get("messages", [])]
            return SessionRecord(meta=meta, messages=messages)
        except Exception as e:
            logger.debug("session load error: %s", e)
            return None

    @staticmethod
    def format_list(sessions: list[SessionMeta]) -> str:
        """Return a human-readable listing of sessions."""
        if not sessions:
            return "No saved sessions."
        import datetime
        lines = ["Recent sessions:\n"]
        for i, s in enumerate(sessions, 1):
            dt = datetime.datetime.fromtimestamp(s.updated_at).strftime("%Y-%m-%d %H:%M")
            model_tag = f"[{s.model}]" if s.model else ""
            lines.append(
                f"  {i:>3}.  {dt}  {model_tag}  {s.title[:60]}"
            )
        lines.append(
            "\nUse /history <n> to load session n, or /history list for more."
        )
        return "\n".join(lines)
