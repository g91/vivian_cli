"""Message mapper utilities — mirrors src/utils/messages/mappers.ts"""
from __future__ import annotations

import re
import uuid as _uuid_mod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Type aliases (mirroring TypeScript interfaces as plain dicts)
# ---------------------------------------------------------------------------

SDKCompactMetadata = Dict[str, Any]
Message = Dict[str, Any]
SDKMessage = Dict[str, Any]


# ---------------------------------------------------------------------------
# toInternalMessages
# ---------------------------------------------------------------------------

def to_internal_messages(messages: List[SDKMessage]) -> List[Message]:
    """Convert SDK wire messages to internal Message dicts."""
    result: List[Message] = []
    now = datetime.now(timezone.utc).isoformat()
    for message in messages:
        msg_type = message.get("type")
        if msg_type == "assistant":
            result.append({
                "type": "assistant",
                "message": message.get("message"),
                "uuid": message.get("uuid"),
                "requestId": None,
                "timestamp": now,
            })
        elif msg_type == "user":
            result.append({
                "type": "user",
                "message": message.get("message"),
                "uuid": message.get("uuid") or str(_uuid_mod.uuid4()),
                "timestamp": message.get("timestamp") or now,
                "isMeta": message.get("isSynthetic"),
            })
        elif msg_type == "system":
            if message.get("subtype") == "compact_boundary":
                result.append({
                    "type": "system",
                    "content": "Conversation compacted",
                    "level": "info",
                    "subtype": "compact_boundary",
                    "compactMetadata": from_sdk_compact_metadata(
                        message.get("compact_metadata", {})
                    ),
                    "uuid": message.get("uuid"),
                    "timestamp": now,
                })
    return result


# camelCase alias
toInternalMessages = to_internal_messages


# ---------------------------------------------------------------------------
# compact_metadata converters
# ---------------------------------------------------------------------------

def to_sdk_compact_metadata(meta: Dict[str, Any]) -> SDKCompactMetadata:
    """Convert internal CompactMetadata to SDK wire format."""
    seg = meta.get("preservedSegment")
    out: Dict[str, Any] = {
        "trigger": meta.get("trigger"),
        "pre_tokens": meta.get("preTokens"),
    }
    if seg:
        out["preserved_segment"] = {
            "head_uuid": seg.get("headUuid"),
            "anchor_uuid": seg.get("anchorUuid"),
            "tail_uuid": seg.get("tailUuid"),
        }
    return out


toSDKCompactMetadata = to_sdk_compact_metadata


def from_sdk_compact_metadata(meta: SDKCompactMetadata) -> Dict[str, Any]:
    """Convert SDK compact_metadata to internal CompactMetadata format."""
    seg = meta.get("preserved_segment")
    out: Dict[str, Any] = {
        "trigger": meta.get("trigger"),
        "preTokens": meta.get("pre_tokens"),
    }
    if seg:
        out["preservedSegment"] = {
            "headUuid": seg.get("head_uuid"),
            "anchorUuid": seg.get("anchor_uuid"),
            "tailUuid": seg.get("tail_uuid"),
        }
    return out


fromSDKCompactMetadata = from_sdk_compact_metadata


# ---------------------------------------------------------------------------
# toSDKMessages
# ---------------------------------------------------------------------------

def to_sdk_messages(messages: List[Message]) -> List[SDKMessage]:
    """Convert internal Message dicts to SDK wire messages."""
    result: List[SDKMessage] = []
    for message in messages:
        msg_type = message.get("type")
        if msg_type == "assistant":
            sdk_msg: Dict[str, Any] = {
                "type": "assistant",
                "message": message.get("message"),
                "session_id": None,
                "parent_tool_use_id": None,
                "uuid": message.get("uuid"),
                "error": message.get("error"),
            }
            result.append(sdk_msg)
        elif msg_type == "user":
            sdk_user: Dict[str, Any] = {
                "type": "user",
                "message": message.get("message"),
                "session_id": None,
                "parent_tool_use_id": None,
                "uuid": message.get("uuid"),
                "timestamp": message.get("timestamp"),
                "isSynthetic": message.get("isMeta") or message.get("isVisibleInTranscriptOnly"),
            }
            if message.get("toolUseResult") is not None:
                mcp_meta = message.get("mcpMeta")
                if isinstance(mcp_meta, dict):
                    sdk_user["tool_use_result"] = {
                        "content": message["toolUseResult"],
                        **mcp_meta,
                    }
                else:
                    sdk_user["tool_use_result"] = message["toolUseResult"]
            result.append(sdk_user)
        elif msg_type == "system":
            subtype = message.get("subtype")
            if subtype == "compact_boundary" and message.get("compactMetadata"):
                result.append({
                    "type": "system",
                    "subtype": "compact_boundary",
                    "session_id": None,
                    "uuid": message.get("uuid"),
                    "compact_metadata": to_sdk_compact_metadata(message["compactMetadata"]),
                })
            elif subtype == "local_command":
                content = message.get("content", "")
                if "<local-command-stdout>" in content or "<local-command-stderr>" in content:
                    sdk_assistant = local_command_output_to_sdk_assistant_message(
                        content, message.get("uuid", str(_uuid_mod.uuid4()))
                    )
                    result.append(sdk_assistant)
    return result


toSDKMessages = to_sdk_messages


# ---------------------------------------------------------------------------
# localCommandOutputToSDKAssistantMessage
# ---------------------------------------------------------------------------

def local_command_output_to_sdk_assistant_message(
    raw_content: str,
    msg_uuid: str,
) -> SDKMessage:
    """Convert local command output (e.g. /cost) to an SDK assistant message.

    Strips ANSI escape codes and unwraps the XML wrapper tags.
    """
    # Strip ANSI escape codes
    ansi_escape = re.compile(r'\x1B\[[0-9;]*[mGKHF]')
    clean = ansi_escape.sub("", raw_content)
    clean = re.sub(r'<local-command-stdout>([\s\S]*?)</local-command-stdout>', r'\1', clean)
    clean = re.sub(r'<local-command-stderr>([\s\S]*?)</local-command-stderr>', r'\1', clean)
    clean = clean.strip()

    return {
        "type": "assistant",
        "message": {
            "id": f"msg_{_uuid_mod.uuid4().hex[:24]}",
            "type": "message",
            "role": "assistant",
            "content": clean,
            "model": "SYNTHETIC",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 0, "output_tokens": 0},
        },
        "parent_tool_use_id": None,
        "session_id": None,
        "uuid": msg_uuid,
    }


localCommandOutputToSDKAssistantMessage = local_command_output_to_sdk_assistant_message


# ---------------------------------------------------------------------------
# toSDKRateLimitInfo
# ---------------------------------------------------------------------------

def to_sdk_rate_limit_info(limits: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Map internal vivianAILimits to SDK-facing SDKRateLimitInfo, dropping internal fields."""
    if not limits:
        return None
    keep = (
        "status", "resetsAt", "rateLimitType", "utilization",
        "overageStatus", "overageResetsAt", "overageDisabledReason",
        "isUsingOverage", "surpassedThreshold",
    )
    return {k: limits[k] for k in keep if k in limits}


toSDKRateLimitInfo = to_sdk_rate_limit_info


def normalizeAssistantMessageForSDK(message):
    """Normalizes tool inputs in assistant message content for SDK consumption."""
    result = None
    _input = message
    _output = _input if _input is not None else {}
    return _output

