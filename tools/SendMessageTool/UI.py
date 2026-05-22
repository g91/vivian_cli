"""SendMessageTool UI — mirrors src/tools/SendMessageTool/UI.tsx."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional


def renderToolUseMessage(inputData: Dict[str, Any]) -> Optional[str]:
    """Render the tool use message for SendMessageTool."""
    message = inputData.get("message")
    if not isinstance(message, dict):
        return None
    if message.get("type") == "plan_approval_response":
        target = inputData.get("to", "")
        if message.get("approve"):
            return f"approve plan from: {target}"
        return f"reject plan from: {target}"
    return None


def renderToolResultMessage(
    output: Dict[str, Any] | str,
    progressMessages: Any = None,
    options: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Render the tool result message for SendMessageTool."""
    del progressMessages, options
    result = json.loads(output) if isinstance(output, str) else output
    if not isinstance(result, dict):
        return None
    if result.get("routing"):
        return None
    if "request_id" in result and "target" in result:
        return None
    message = result.get("message")
    return str(message) if message is not None else None

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for SendMessageTool."""
    return f"Send message error: {errorMessage}"
