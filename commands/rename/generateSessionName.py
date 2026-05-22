"""generateSessionName — mirrors src/commands/rename/generateSessionName.ts.

Auto-generate a session name from the first user prompt.
"""

from __future__ import annotations


def generateSessionName(first_prompt: str = "") -> str:
    """Generate a short session name from the first prompt."""
    if not first_prompt:
        return "Untitled session"
    name = first_prompt.strip()[:50]
    if len(first_prompt) > 50:
        name = name.rsplit(" ", 1)[0] + "..."
    return name


generate_session_name = generateSessionName
