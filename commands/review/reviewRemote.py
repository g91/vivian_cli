"""reviewRemote — mirrors src/commands/review/reviewRemote.ts.

Remote review functionality for bridge/headless sessions.
"""

from __future__ import annotations


async def review_remote(pr_number: str = "", session_id: str = "") -> str:
    """Run a remote code review."""
    return f"Remote review started for PR #{pr_number}."
