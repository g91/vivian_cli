"""Companion prompt helpers — mirrors src/buddy/prompt.ts."""
from __future__ import annotations

from typing import Optional

from .companion import get_companion


def companion_intro_text(name: str, species: str) -> str:
    return (
        f"# Companion\n\n"
        f"A small {species} named {name} sits beside the user's input box and "
        f"occasionally comments in a speech bubble. You're not {name} — it's a "
        f"separate watcher.\n\n"
        f"When the user addresses {name} directly (by name), its bubble will answer. "
        f"Your job in that moment is to stay out of the way: respond in ONE line or "
        f"less, or just answer any part of the message meant for you. Don't explain "
        f"that you're not {name} — they know. Don't narrate what {name} might say — "
        f"the bubble handles that."
    )


def get_companion_intro_attachment(messages: Optional[list] = None) -> list[dict]:
    """Return a companion_intro attachment if the companion hasn't been introduced yet."""
    companion = get_companion()
    if not companion:
        return []

    # Skip if already announced for this companion in the current conversation
    for msg in messages or []:
        if isinstance(msg, dict):
            attachment = msg.get("attachment") or msg
            if attachment.get("type") == "companion_intro":
                if attachment.get("name") == companion.name:
                    return []

    return [
        {
            "type": "companion_intro",
            "name": companion.name,
            "species": companion.species,
        }
    ]
