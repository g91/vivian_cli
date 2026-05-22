"""SDK message adapter — mirrors src/remote/sdkMessageAdapter.ts.

Converts SDKMessage from CCR to REPL Message types.

The CCR backend sends SDK-format messages via WebSocket.  The REPL expects
internal Message types for rendering.  This adapter bridges the two.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from ..utils.messages.mappers import from_sdk_compact_metadata

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal converters
# ---------------------------------------------------------------------------

def _convert_assistant_message(msg: dict) -> dict:
    """Convert an SDKAssistantMessage to an AssistantMessage."""
    return {
        "type": "assistant",
        "message": msg.get("message"),
        "uuid": msg.get("uuid", str(uuid4())),
        "requestId": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error": msg.get("error"),
    }


def _convert_stream_event(msg: dict) -> dict:
    """Convert an SDKPartialAssistantMessage (streaming) to a StreamEvent."""
    return {
        "type": "stream_event",
        "event": msg.get("event"),
    }


def _convert_result_message(msg: dict) -> dict:
    """Convert an SDKResultMessage to a SystemMessage."""
    is_error = msg.get("subtype") != "success"
    content = (
        ", ".join(msg["errors"]) if is_error and msg.get("errors")
        else "Unknown error" if is_error
        else "Session completed successfully"
    )
    return {
        "type": "system",
        "subtype": "informational",
        "content": content,
        "level": "warning" if is_error else "info",
        "uuid": msg.get("uuid", str(uuid4())),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _convert_init_message(msg: dict) -> dict:
    """Convert an SDKSystemMessage (init) to a SystemMessage."""
    return {
        "type": "system",
        "subtype": "informational",
        "content": f"Remote session initialized (model: {msg.get('model', '')})",
        "level": "info",
        "uuid": msg.get("uuid", str(uuid4())),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _convert_status_message(msg: dict) -> Optional[dict]:
    """Convert an SDKStatusMessage to a SystemMessage, or None to ignore."""
    status = msg.get("status")
    if not status:
        return None
    content = (
        "Compacting conversation…" if status == "compacting" else f"Status: {status}"
    )
    return {
        "type": "system",
        "subtype": "informational",
        "content": content,
        "level": "info",
        "uuid": msg.get("uuid", str(uuid4())),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _convert_tool_progress_message(msg: dict) -> dict:
    """Convert an SDKToolProgressMessage to a SystemMessage."""
    return {
        "type": "system",
        "subtype": "informational",
        "content": (
            f"Tool {msg.get('tool_name')} running for "
            f"{msg.get('elapsed_time_seconds')}s…"
        ),
        "level": "info",
        "uuid": msg.get("uuid", str(uuid4())),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "toolUseID": msg.get("tool_use_id"),
    }


def _convert_compact_boundary_message(msg: dict) -> dict:
    """Convert an SDKCompactBoundaryMessage to a SystemMessage."""
    return {
        "type": "system",
        "subtype": "compact_boundary",
        "content": "Conversation compacted",
        "level": "info",
        "uuid": msg.get("uuid", str(uuid4())),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "compactMetadata": from_sdk_compact_metadata(msg.get("compact_metadata", {})),
    }


def _create_user_message(content: Any, msg: dict) -> dict:
    """Create a UserMessage from content."""
    tool_use_result = msg.get("tool_use_result")
    mcp_meta = None
    normalized_tool_use_result = tool_use_result
    if isinstance(tool_use_result, dict) and any(
        key in tool_use_result for key in ("content", "_meta", "structuredContent")
    ):
        normalized_tool_use_result = tool_use_result.get("content")
        mcp_meta = {}
        if isinstance(tool_use_result.get("_meta"), dict):
            mcp_meta["_meta"] = tool_use_result["_meta"]
        if isinstance(tool_use_result.get("structuredContent"), dict):
            mcp_meta["structuredContent"] = tool_use_result["structuredContent"]
        if not mcp_meta:
            mcp_meta = None

    return {
        "type": "user",
        "message": {
            "role": "user",
            "content": content,
        },
        "toolUseResult": normalized_tool_use_result,
        **({"mcpMeta": mcp_meta} if mcp_meta else {}),
        "uuid": msg.get("uuid", str(uuid4())),
        "timestamp": msg.get("timestamp", datetime.now(timezone.utc).isoformat()),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def convert_sdk_message(
    msg: dict,
    convert_tool_results: bool = False,
    convert_user_text_messages: bool = False,
) -> dict:
    """Convert an SDKMessage to REPL message format.

    Returns one of:
      {'type': 'message', 'message': <dict>}
      {'type': 'stream_event', 'event': <dict>}
      {'type': 'ignored'}

    Mirrors convertSDKMessage() from sdkMessageAdapter.ts.
    """
    msg_type = msg.get("type", "")

    if msg_type == "assistant":
        return {"type": "message", "message": _convert_assistant_message(msg)}

    if msg_type == "user":
        content = (msg.get("message") or {}).get("content")
        # Tool result messages from the remote server
        is_tool_result = (
            isinstance(content, list)
            and any(b.get("type") == "tool_result" for b in content)
        )
        if convert_tool_results and is_tool_result:
            return {"type": "message", "message": _create_user_message(content, msg)}
        if convert_user_text_messages and not is_tool_result:
            if isinstance(content, (str, list)):
                return {"type": "message", "message": _create_user_message(content, msg)}
        return {"type": "ignored"}

    if msg_type == "stream_event":
        return {"type": "stream_event", "event": _convert_stream_event(msg)}

    if msg_type == "result":
        # Only show result messages for errors
        if msg.get("subtype") != "success":
            return {"type": "message", "message": _convert_result_message(msg)}
        return {"type": "ignored"}

    if msg_type == "system":
        subtype = msg.get("subtype")
        if subtype == "init":
            return {"type": "message", "message": _convert_init_message(msg)}
        if subtype == "status":
            status_msg = _convert_status_message(msg)
            return (
                {"type": "message", "message": status_msg}
                if status_msg
                else {"type": "ignored"}
            )
        if subtype == "compact_boundary":
            return {
                "type": "message",
                "message": _convert_compact_boundary_message(msg),
            }
        log.debug("[sdkMessageAdapter] Ignoring system message subtype: %s", subtype)
        return {"type": "ignored"}

    if msg_type == "tool_progress":
        return {"type": "message", "message": _convert_tool_progress_message(msg)}

    if msg_type == "auth_status":
        log.debug("[sdkMessageAdapter] Ignoring auth_status message")
        return {"type": "ignored"}

    if msg_type == "tool_use_summary":
        log.debug("[sdkMessageAdapter] Ignoring tool_use_summary message")
        return {"type": "ignored"}

    if msg_type == "rate_limit_event":
        log.debug("[sdkMessageAdapter] Ignoring rate_limit_event message")
        return {"type": "ignored"}

    log.debug("[sdkMessageAdapter] Unknown message type: %s", msg_type)
    return {"type": "ignored"}


def is_session_end_message(msg: dict) -> bool:
    """Check if an SDKMessage indicates the session has ended."""
    return msg.get("type") == "result"


def is_success_result(msg: dict) -> bool:
    """Check if an SDKResultMessage indicates success."""
    return msg.get("subtype") == "success"


def get_result_text(msg: dict) -> Optional[str]:
    """Extract the result text from a successful SDKResultMessage."""
    if msg.get("subtype") == "success":
        return msg.get("result")
    return None


# re-export for backward compat
from typing import Any  # noqa: E402
