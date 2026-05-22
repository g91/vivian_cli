"""Tool utilities — mirrors src/tools/utils.ts"""
from __future__ import annotations
from typing import Any, List, Optional


def tagMessagesWithToolUseID(
    messages: List[Any],
    toolUseID: Optional[str],
) -> List[Any]:
    """
    Tags user messages with a sourceToolUseID so they stay transient until the
    tool resolves. Prevents the "is running" message from being duplicated in UI.
    """
    if not toolUseID:
        return messages
    result = []
    for m in messages:
        if isinstance(m, dict) and m.get("type") == "user":
            result.append({**m, "sourceToolUseID": toolUseID})
        else:
            result.append(m)
    return result


def getToolUseIDFromParentMessage(
    parentMessage: Any,
    toolName: str,
) -> Optional[str]:
    """Extracts the tool use ID from a parent message for a given tool name."""
    content: Any = None
    if isinstance(parentMessage, dict):
        content = parentMessage.get("message", {}).get("content", [])
    if not content:
        return None
    for block in content:
        if (
            isinstance(block, dict)
            and block.get("type") == "tool_use"
            and block.get("name") == toolName
        ):
            return block.get("id")
    return None


# Legacy snake_case aliases for backward compatibility
tag_messages_with_tool_use_id = tagMessagesWithToolUseID
get_tool_use_id_from_parent_message = getToolUseIDFromParentMessage
