"""SendMessageTool — mirrors src/tools/SendMessageTool/SendMessageTool.tsx"""
from __future__ import annotations
from typing import Any, Dict

TOOL_NAME = "SendMessage"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["message"],
    "properties": {
        "message": {"type": "string", "description": "Message to send to the user"},
        "type": {
            "type": "string",
            "enum": ["info", "warning", "error", "success"],
            "default": "info",
        },
    },
}


async def description() -> str:
    return "Send a message to the user or a channel."


async def prompt() -> str:
    return "Use this tool to send a message to the user or a notification channel."


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    message = input_data.get("message", "")
    msg_type = input_data.get("type", "info")
    print(f"[{msg_type.upper()}] {message}")
    return {"sent": True, "message": message}
