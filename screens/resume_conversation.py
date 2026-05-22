"""ResumeConversation screen — mirrors src/screens/ResumeConversation.tsx.

Screen for browsing and resuming past conversations.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)


def _parse_pr_identifier(value: str) -> Optional[int]:
    """Parse a PR number or GitHub URL into an int.  Returns None if not valid."""
    try:
        n = int(value, 10)
        if n > 0:
            return n
    except (ValueError, TypeError):
        pass

    import re
    m = re.search(r"github\.com/[^/]+/[^/]+/pull/(\d+)", value)
    if m:
        return int(m.group(1))
    return None


@dataclass
class SessionLogEntry:
    session_id: str
    created_at: float
    last_active_at: float
    cwd: str
    title: Optional[str] = None
    message_count: int = 0


@dataclass
class ResumeConversationConfig:
    commands: list[dict] = field(default_factory=list)
    worktree_paths: list[str] = field(default_factory=list)
    initial_tools: list[Any] = field(default_factory=list)
    mcp_clients: list[Any] = field(default_factory=list)
    debug: bool = False
    system_prompt: Optional[str] = None
    append_system_prompt: Optional[str] = None
    initial_search_query: Optional[str] = None
    disable_slash_commands: bool = False
    fork_session: bool = False
    filter_by_pr: Any = None
    thinking_config: Optional[dict] = None
    on_turn_complete: Optional[Callable] = None


class ResumeConversation:
    """ResumeConversation screen controller.

    Mirrors ResumeConversation.tsx — shows a list of past sessions and
    lets the user select one to resume.
    """

    def __init__(self, config: ResumeConversationConfig) -> None:
        self._config = config
        self._sessions: list[SessionLogEntry] = []
        self._selected_index: int = 0
        self._search_query: str = config.initial_search_query or ""
        self._loading: bool = False

    def load_sessions(self, sessions: list[dict]) -> None:
        """Load session log entries from serialized dicts."""
        self._sessions = [
            SessionLogEntry(
                session_id=s["session_id"],
                created_at=s.get("created_at", 0.0),
                last_active_at=s.get("last_active_at", 0.0),
                cwd=s.get("cwd", ""),
                title=s.get("title"),
                message_count=s.get("message_count", 0),
            )
            for s in sessions
        ]
        # Apply PR filter if configured
        if self._config.filter_by_pr:
            pr_num = _parse_pr_identifier(str(self._config.filter_by_pr))
            if pr_num:
                self._sessions = [
                    s for s in self._sessions
                    if str(pr_num) in (s.title or "")
                ]

    @property
    def sessions(self) -> list[SessionLogEntry]:
        return self._sessions

    @property
    def selected(self) -> Optional[SessionLogEntry]:
        if 0 <= self._selected_index < len(self._sessions):
            return self._sessions[self._selected_index]
        return None

    def select_next(self) -> None:
        if self._sessions:
            self._selected_index = min(
                self._selected_index + 1, len(self._sessions) - 1
            )

    def select_prev(self) -> None:
        if self._sessions:
            self._selected_index = max(self._selected_index - 1, 0)

    def set_search_query(self, query: str) -> None:
        self._search_query = query
        self._selected_index = 0

    def get_filtered_sessions(self) -> list[SessionLogEntry]:
        if not self._search_query:
            return self._sessions
        q = self._search_query.lower()
        return [
            s for s in self._sessions
            if q in (s.title or "").lower() or q in s.cwd.lower()
        ]

    def get_selected_session_id(self) -> Optional[str]:
        sel = self.selected
        return sel.session_id if sel else None
