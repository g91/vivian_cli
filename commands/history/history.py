"""history command — mirrors src/commands/history/history.tsx.

Show command history from the current session.
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from ...utils.listSessionsImpl import listSessionsImpl
from ..resume.resume import resumeSession

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


def formatHistory(entries: list, limit: int = 20) -> str:
    if not entries:
        return "No history."
    lines = ["Command History:", ""]
    for i, entry in enumerate(entries[-limit:], 1):
        lines.append(f"  {i:>3}. {str(entry)[:100]}")
    return "\n".join(lines)


def _history_context_dir(context: CommandContext) -> str | None:
    engine = getattr(context, "engine", None)
    if engine is None:
        engine = getattr(context, "query_engine", None)
    return getattr(engine, "cwd", None) or getattr(context, "cwd", None)


def _format_recent_sessions(sessions: list[dict]) -> str:
    if not sessions:
        return "No saved sessions."

    lines = ["Recent sessions:", ""]
    for index, session in enumerate(sessions, 1):
        last_modified = session.get("lastModified") or 0
        timestamp = (
            datetime.datetime.fromtimestamp(last_modified / 1000).strftime("%Y-%m-%d %H:%M")
            if last_modified
            else "unknown time"
        )
        title = str(session.get("customTitle") or session.get("summary") or session.get("firstPrompt") or "")
        lines.append(f"  {index:>3}.  {timestamp}  {title[:60]}")
    lines.append("")
    lines.append("Use /history <n> to load session n, or /resume <id> to resume directly.")
    return "\n".join(lines)


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    subarg = args.strip() if args else ""

    try:
        sessions = await listSessionsImpl(
            {
                "dir": _history_context_dir(context),
                "limit": 20,
                "includeWorktrees": True,
            }
        )
    except Exception:
        sessions = []

    if subarg.isdigit():
        idx = int(subarg) - 1
        if idx < 0 or idx >= len(sessions):
            return TextResult(f"No session {subarg}. Use /history to list sessions.")

        session_id = sessions[idx].get("sessionId")
        if not isinstance(session_id, str) or not session_id:
            return TextResult(f"Could not load session {subarg}.")

        result = await resumeSession(session_id, context)
        return TextResult(getattr(result, "value", str(result)))

    if not subarg:
        return TextResult(_format_recent_sessions(sessions))

    try:
        app_state = getattr(context, "app_state", None)
        if app_state and hasattr(app_state, "command_history"):
            try:
                limit = int(subarg)
            except ValueError:
                limit = 20
            return TextResult(formatHistory(app_state.command_history, limit))
    except Exception:
        pass
    return TextResult("No command history available.")


format_history = formatHistory
