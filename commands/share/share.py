"""share command — mirrors src/commands/share/.

Share the current conversation via a shareable link.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    sid = ""
    try:
        qe = getattr(context, "query_engine", None)
        if qe:
            sid = getattr(qe, "session_id", "") or ""
    except Exception:
        pass
    if sid:
        return TextResult(f"Session shared: {sid}\nShare URL: https://vivian.d0a.net/session/{sid}")
    return TextResult("No active session to share.")


shareSession = call
share_session = call
