"""Remote permission bridge — mirrors src/remote/remotePermissionBridge.ts.

Creates synthetic assistant messages and tool stubs for remote permission
requests where we don't have the real local equivalents.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def create_synthetic_assistant_message(
    request: dict,
    request_id: str,
) -> dict:
    """Create a synthetic AssistantMessage for remote permission requests.

    The ToolUseConfirm type requires an AssistantMessage, but in remote mode
    we don't have a real one — the tool use runs on the CCR container.

    Mirrors createSyntheticAssistantMessage() from remotePermissionBridge.ts.
    """
    return {
        "type": "assistant",
        "uuid": str(uuid4()),
        "message": {
            "id": f"remote-{request_id}",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": request.get("tool_use_id"),
                    "name": request.get("tool_name"),
                    "input": request.get("input"),
                }
            ],
            "model": "",
            "stop_reason": None,
            "stop_sequence": None,
            "container": None,
            "context_management": None,
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        },
        "request_id": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def create_tool_stub(tool_name: str) -> dict:
    """Create a minimal Tool stub for tools not loaded locally.

    This happens when the remote CCR has tools (e.g., MCP tools) that the
    local CLI doesn't know about.  The stub routes to FallbackPermissionRequest.

    Mirrors createToolStub() from remotePermissionBridge.ts.
    """

    def render_tool_use_message(input_data: dict) -> str:
        entries = list(input_data.items())
        if not entries:
            return ""
        parts = []
        for key, value in entries[:3]:
            value_str = value if isinstance(value, str) else json.dumps(value)
            parts.append(f"{key}: {value_str}")
        return ", ".join(parts)

    async def _call(*args: Any, **kwargs: Any) -> dict:
        return {"data": ""}

    async def _description(*args: Any, **kwargs: Any) -> str:
        return ""

    return {
        "name": tool_name,
        "input_schema": {},
        "is_enabled": lambda: True,
        "user_facing_name": lambda: tool_name,
        "render_tool_use_message": render_tool_use_message,
        "call": _call,
        "description": _description,
        "prompt": lambda: "",
        "is_read_only": lambda: False,
        "is_mcp": False,
        "needs_permissions": lambda: True,
    }
