"""
Port of src/utils/directMemberMessage.ts
"""
from __future__ import annotations

from typing import Any
import re
from datetime import datetime, timezone


DirectMessageResult = Any
WriteToMailboxFn = Any


def parseDirectMemberMessage(input):
    """Parse `@agent-name message` syntax for direct team member messaging."""
    if not isinstance(input, str):
        return None
    match = re.match(r"^@([\w-]+)\s+(.+)$", input, re.DOTALL)
    if not match:
        return None
    recipient_name = match.group(1)
    message = match.group(2).strip()
    if not recipient_name or not message:
        return None
    return {"recipientName": recipient_name, "message": message}


async def sendDirectMemberMessage(recipientName, message, teamContext, writeToMailbox=None):
    """Send a direct message to a team member, bypassing the model."""
    if not teamContext or not writeToMailbox:
        return {"success": False, "error": "no_team_context"}

    teammates = teamContext.get("teammates", {}) if isinstance(teamContext, dict) else getattr(teamContext, "teammates", {})
    team_name = teamContext.get("teamName") if isinstance(teamContext, dict) else getattr(teamContext, "teamName", None)
    member = None
    for teammate in (teammates or {}).values():
        teammate_name = teammate.get("name") if isinstance(teammate, dict) else getattr(teammate, "name", None)
        if teammate_name == recipientName:
            member = teammate
            break

    if member is None:
        return {"success": False, "error": "unknown_recipient", "recipientName": recipientName}

    await writeToMailbox(
        recipientName,
        {
            "from": "user",
            "text": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        team_name,
    )
    return {"success": True, "recipientName": recipientName}


parse_direct_member_message = parseDirectMemberMessage
send_direct_member_message = sendDirectMemberMessage

