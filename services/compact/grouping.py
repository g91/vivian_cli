"""Message grouping by API round — mirrors src/services/compact/grouping.ts."""
from __future__ import annotations

from typing import Optional


def groupMessagesByApiRound(messages: list[dict]) -> list[list[dict]]:
    """Group messages at API-round boundaries.

    One group per API round-trip. A boundary fires when a new assistant
    response begins (different message.id from the prior assistant).

    Mirrors groupMessagesByApiRound() from grouping.ts.
    """
    groups: list[list[dict]] = []
    current: list[dict] = []
    last_assistant_id: Optional[str] = None

    for msg in messages:
        msg_type = msg.get("type")
        if msg_type == "assistant":
            msg_id = msg.get("message", {}).get("id") or msg.get("id")
            if msg_id != last_assistant_id and current:
                groups.append(current)
                current = [msg]
            else:
                current.append(msg)
            last_assistant_id = msg_id
        else:
            current.append(msg)

    if current:
        groups.append(current)

    return groups


group_messages_by_api_round = groupMessagesByApiRound
