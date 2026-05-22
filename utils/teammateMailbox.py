"""Port of src/utils/teammateMailbox.ts."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..tools.SendMessageTool.constants import SEND_MESSAGE_TOOL_NAME
from .debug import logForDebugging
from .envUtils import get_teams_dir
from .lockfile import lock
from .swarm.constants import TEAM_LEAD_NAME
from .tasks import sanitizePathComponent
from .teammate import getAgentName, getTeammateColor, getTeamName


TEAMMATE_MESSAGE_TAG = "teammate-message"
VALID_PERMISSION_MODES = {"default", "acceptEdits", "bypassPermissions", "dontAsk", "plan"}
TeammateMessage = dict[str, Any]
IdleNotificationMessage = dict[str, Any]
PermissionRequestMessage = dict[str, Any]
PermissionResponseMessage = dict[str, Any]
SandboxPermissionRequestMessage = dict[str, Any]
SandboxPermissionResponseMessage = dict[str, Any]
PlanApprovalRequestMessage = dict[str, Any]
PlanApprovalResponseMessage = dict[str, Any]
ShutdownRequestMessage = dict[str, Any]
ShutdownApprovedMessage = dict[str, Any]
ShutdownRejectedMessage = dict[str, Any]
TaskAssignmentMessage = dict[str, Any]
TeamPermissionUpdateMessage = dict[str, Any]
ModeSetRequestMessage = dict[str, Any]
PlanApprovalRequestMessageSchema: Any = None
PlanApprovalResponseMessageSchema: Any = None
ShutdownRequestMessageSchema: Any = None
ShutdownApprovedMessageSchema: Any = None
ShutdownRejectedMessageSchema: Any = None
ModeSetRequestMessageSchema: Any = None


def getInboxPath(agentName: str, teamName: str | None = None) -> str:
    team = teamName or getTeamName() or "default"
    safe_team = sanitizePathComponent(team)
    safe_agent_name = sanitizePathComponent(agentName)
    inbox_dir = Path(get_teams_dir()) / safe_team / "inboxes"
    full_path = inbox_dir / f"{safe_agent_name}.json"
    logForDebugging(
        f"[TeammateMailbox] getInboxPath: agent={agentName}, team={team}, fullPath={full_path}"
    )
    return str(full_path)


async def ensureInboxDir(teamName: str | None = None) -> None:
    team = teamName or getTeamName() or "default"
    safe_team = sanitizePathComponent(team)
    inbox_dir = Path(get_teams_dir()) / safe_team / "inboxes"
    inbox_dir.mkdir(parents=True, exist_ok=True)


async def readMailbox(agentName: str, teamName: str | None = None) -> list[TeammateMessage]:
    inbox_path = Path(getInboxPath(agentName, teamName))
    try:
        return json.loads(inbox_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except Exception as error:
        logForDebugging(f"Failed to read inbox for {agentName}: {error}")
        return []


async def readUnreadMessages(agentName: str, teamName: str | None = None) -> list[TeammateMessage]:
    messages = await readMailbox(agentName, teamName)
    return [m for m in messages if not m.get("read")]


async def writeToMailbox(
    recipientName: str,
    message: dict[str, Any],
    teamName: str | None = None,
) -> None:
    await ensureInboxDir(teamName)
    inbox_path = Path(getInboxPath(recipientName, teamName))
    if not inbox_path.exists():
        inbox_path.write_text("[]", encoding="utf-8")
    release = None
    try:
        release = lock(str(inbox_path), timeout_ms=10_000)
        messages = await readMailbox(recipientName, teamName)
        messages.append({**message, "read": False})
        inbox_path.write_text(json.dumps(messages, indent=2), encoding="utf-8")
    finally:
        if release is not None:
            release()


async def markMessageAsReadByIndex(agentName: str, teamName: str | None, messageIndex: int) -> None:
    inbox_path = Path(getInboxPath(agentName, teamName))
    if not inbox_path.exists():
        return
    release = None
    try:
        release = lock(str(inbox_path), timeout_ms=10_000)
        messages = await readMailbox(agentName, teamName)
        if 0 <= messageIndex < len(messages) and not messages[messageIndex].get("read"):
            messages[messageIndex] = {**messages[messageIndex], "read": True}
            inbox_path.write_text(json.dumps(messages, indent=2), encoding="utf-8")
    finally:
        if release is not None:
            release()


async def markMessagesAsRead(agentName: str, teamName: str | None = None) -> None:
    await markMessagesAsReadByPredicate(agentName, lambda _msg: True, teamName)


async def clearMailbox(agentName: str, teamName: str | None = None) -> None:
    inbox_path = Path(getInboxPath(agentName, teamName))
    if inbox_path.exists():
        inbox_path.write_text("[]", encoding="utf-8")


def formatTeammateMessages(messages=None) -> str:
    messages = messages or []
    rendered = []
    for message in messages:
        color_attr = f' color="{message["color"]}"' if message.get("color") else ""
        summary_attr = f' summary="{message["summary"]}"' if message.get("summary") else ""
        rendered.append(
            f'<{TEAMMATE_MESSAGE_TAG} teammate_id="{message.get("from", "")}"{color_attr}{summary_attr}>\n{message.get("text", "")}\n</{TEAMMATE_MESSAGE_TAG}>'
        )
    return "\n\n".join(rendered)


def createIdleNotification(agentId, options=None) -> IdleNotificationMessage:
    options = options or {}
    return {
        "type": "idle_notification",
        "from": agentId,
        "timestamp": _now_iso(),
        "idleReason": options.get("idleReason"),
        "summary": options.get("summary"),
        "completedTaskId": options.get("completedTaskId"),
        "completedStatus": options.get("completedStatus"),
        "failureReason": options.get("failureReason"),
    }


def isIdleNotification(messageText):
    return _parse_typed_message(messageText, "idle_notification")


def createPermissionRequestMessage(params=None) -> PermissionRequestMessage:
    params = params or {}
    return {
        "type": "permission_request",
        "request_id": params["request_id"],
        "agent_id": params["agent_id"],
        "tool_name": params["tool_name"],
        "tool_use_id": params["tool_use_id"],
        "description": params["description"],
        "input": params.get("input") or {},
        "permission_suggestions": params.get("permission_suggestions") or [],
    }


def createPermissionResponseMessage(params=None) -> PermissionResponseMessage:
    params = params or {}
    if params.get("subtype") == "error":
        return {
            "type": "permission_response",
            "request_id": params["request_id"],
            "subtype": "error",
            "error": params.get("error") or "Permission denied",
        }
    return {
        "type": "permission_response",
        "request_id": params["request_id"],
        "subtype": "success",
        "response": {
            "updated_input": params.get("updated_input"),
            "permission_updates": params.get("permission_updates"),
        },
    }


def isPermissionRequest(messageText):
    return _parse_typed_message(messageText, "permission_request")


def isPermissionResponse(messageText):
    return _parse_typed_message(messageText, "permission_response")


def createSandboxPermissionRequestMessage(params=None) -> SandboxPermissionRequestMessage:
    params = params or {}
    return {
        "type": "sandbox_permission_request",
        "requestId": params["requestId"],
        "workerId": params["workerId"],
        "workerName": params["workerName"],
        "workerColor": params.get("workerColor"),
        "hostPattern": {"host": params["host"]},
        "createdAt": _now_ms(),
    }


def createSandboxPermissionResponseMessage(params) -> SandboxPermissionResponseMessage:
    return {
        "type": "sandbox_permission_response",
        "requestId": params["requestId"],
        "host": params["host"],
        "allow": bool(params["allow"]),
        "timestamp": _now_iso(),
    }


def isSandboxPermissionRequest(messageText):
    return _parse_typed_message(messageText, "sandbox_permission_request")


def isSandboxPermissionResponse(messageText):
    return _parse_typed_message(messageText, "sandbox_permission_response")


def createShutdownRequestMessage(params=None) -> ShutdownRequestMessage:
    params = params or {}
    return {
        "type": "shutdown_request",
        "requestId": params["requestId"],
        "from": params["from"],
        "reason": params.get("reason"),
        "timestamp": _now_iso(),
    }


def createShutdownApprovedMessage(params=None) -> ShutdownApprovedMessage:
    params = params or {}
    return {
        "type": "shutdown_approved",
        "requestId": params["requestId"],
        "from": params["from"],
        "timestamp": _now_iso(),
        "paneId": params.get("paneId"),
        "backendType": params.get("backendType"),
    }


def createShutdownRejectedMessage(params) -> ShutdownRejectedMessage:
    return {
        "type": "shutdown_rejected",
        "requestId": params["requestId"],
        "from": params["from"],
        "reason": params["reason"],
        "timestamp": _now_iso(),
    }


async def sendShutdownRequestToMailbox(targetName, teamName=None, reason=None):
    resolved_team_name = teamName or getTeamName()
    sender_name = getAgentName() or TEAM_LEAD_NAME
    request_id = _generate_request_id("shutdown", targetName)
    shutdown_message = createShutdownRequestMessage(
        {
            "requestId": request_id,
            "from": sender_name,
            "reason": reason,
        }
    )
    await writeToMailbox(
        targetName,
        {
            "from": sender_name,
            "text": json.dumps(shutdown_message),
            "timestamp": _now_iso(),
            "color": getTeammateColor(),
        },
        resolved_team_name,
    )
    return {"requestId": request_id, "target": targetName}


def isShutdownRequest(messageText):
    payload = _parse_typed_message(messageText, "shutdown_request")
    return payload if _has_fields(payload, {"requestId", "from", "timestamp"}) else None


def isPlanApprovalRequest(messageText):
    payload = _parse_typed_message(messageText, "plan_approval_request")
    return payload if _has_fields(payload, {"from", "timestamp", "planFilePath", "planContent", "requestId"}) else None


def isShutdownApproved(messageText):
    payload = _parse_typed_message(messageText, "shutdown_approved")
    return payload if _has_fields(payload, {"requestId", "from", "timestamp"}) else None


def isShutdownRejected(messageText):
    payload = _parse_typed_message(messageText, "shutdown_rejected")
    return payload if _has_fields(payload, {"requestId", "from", "reason", "timestamp"}) else None


def isPlanApprovalResponse(messageText):
    payload = _parse_typed_message(messageText, "plan_approval_response")
    if not _has_fields(payload, {"requestId", "approved", "timestamp"}):
        return None
    if payload.get("permissionMode") and payload["permissionMode"] not in VALID_PERMISSION_MODES:
        return None
    return payload


def isTaskAssignment(messageText):
    return _parse_typed_message(messageText, "task_assignment")


def isTeamPermissionUpdate(messageText):
    return _parse_typed_message(messageText, "team_permission_update")


def createModeSetRequestMessage(params):
    mode = params["mode"]
    if mode not in VALID_PERMISSION_MODES:
        raise ValueError(f"Invalid permission mode: {mode}")
    return {
        "type": "mode_set_request",
        "mode": mode,
        "from": params["from"],
    }


def isModeSetRequest(messageText):
    payload = _parse_typed_message(messageText, "mode_set_request")
    if not _has_fields(payload, {"mode", "from"}):
        return None
    if payload["mode"] not in VALID_PERMISSION_MODES:
        return None
    return payload


def isStructuredProtocolMessage(messageText):
    payload = _parse_json(messageText)
    if not isinstance(payload, dict) or "type" not in payload:
        return False
    return payload["type"] in {
        "permission_request",
        "permission_response",
        "sandbox_permission_request",
        "sandbox_permission_response",
        "shutdown_request",
        "shutdown_approved",
        "team_permission_update",
        "mode_set_request",
        "plan_approval_request",
        "plan_approval_response",
    }


async def markMessagesAsReadByPredicate(agentName, predicate=None, teamName=None):
    predicate = predicate or (lambda _msg: True)
    inbox_path = Path(getInboxPath(agentName, teamName))
    if not inbox_path.exists():
        return
    release = None
    try:
        release = lock(str(inbox_path), timeout_ms=10_000)
        messages = await readMailbox(agentName, teamName)
        if not messages:
            return
        updated_messages = [
            {**message, "read": True} if (not message.get("read") and predicate(message)) else message
            for message in messages
        ]
        inbox_path.write_text(json.dumps(updated_messages, indent=2), encoding="utf-8")
    finally:
        if release is not None:
            release()


def getLastPeerDmSummary(messages):
    for msg in reversed(messages or []):
        if not msg:
            continue
        if msg.get("type") == "user":
            content = _message_content(msg)
            if isinstance(content, str):
                break
        if msg.get("type") != "assistant":
            continue
        content = _message_content(msg)
        if not isinstance(content, list):
            continue
        for block in content:
            if (
                isinstance(block, dict)
                and block.get("type") == "tool_use"
                and block.get("name") == SEND_MESSAGE_TOOL_NAME
                and isinstance(block.get("input"), dict)
            ):
                input_data = block["input"]
                to_value = input_data.get("to")
                if (
                    isinstance(to_value, str)
                    and to_value != "*"
                    and to_value.lower() != TEAM_LEAD_NAME.lower()
                    and isinstance(input_data.get("message"), str)
                ):
                    summary = input_data.get("summary") if isinstance(input_data.get("summary"), str) else input_data["message"][:80]
                    return f"[to {to_value}] {summary}"
    return None


def _parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return None


def _parse_typed_message(text: str, expected_type: str):
    payload = _parse_json(text)
    if isinstance(payload, dict) and payload.get("type") == expected_type:
        return payload
    return None


def _has_fields(payload: Any, required_fields: set[str]) -> bool:
    return isinstance(payload, dict) and all(field in payload for field in required_fields)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _generate_request_id(prefix: str, target: str) -> str:
    safe_target = sanitizePathComponent(target)
    return f"{prefix}-{safe_target}-{_now_ms()}"


def _message_content(msg: dict[str, Any]) -> Any:
    message_obj = msg.get("message")
    if isinstance(message_obj, dict):
        return message_obj.get("content")
    return None


get_inbox_path = getInboxPath
ensure_inbox_dir = ensureInboxDir
read_mailbox = readMailbox
read_unread_messages = readUnreadMessages
write_to_mailbox = writeToMailbox
mark_message_as_read_by_index = markMessageAsReadByIndex
mark_messages_as_read = markMessagesAsRead
clear_mailbox = clearMailbox
format_teammate_messages = formatTeammateMessages
create_idle_notification = createIdleNotification
is_idle_notification = isIdleNotification
create_permission_request_message = createPermissionRequestMessage
create_permission_response_message = createPermissionResponseMessage
is_permission_request = isPermissionRequest
is_permission_response = isPermissionResponse
create_sandbox_permission_request_message = createSandboxPermissionRequestMessage
create_sandbox_permission_response_message = createSandboxPermissionResponseMessage
is_sandbox_permission_request = isSandboxPermissionRequest
is_sandbox_permission_response = isSandboxPermissionResponse
create_shutdown_request_message = createShutdownRequestMessage
create_shutdown_approved_message = createShutdownApprovedMessage
create_shutdown_rejected_message = createShutdownRejectedMessage
send_shutdown_request_to_mailbox = sendShutdownRequestToMailbox
is_shutdown_request = isShutdownRequest
is_plan_approval_request = isPlanApprovalRequest
is_shutdown_approved = isShutdownApproved
is_shutdown_rejected = isShutdownRejected
is_plan_approval_response = isPlanApprovalResponse
is_task_assignment = isTaskAssignment
is_team_permission_update = isTeamPermissionUpdate
create_mode_set_request_message = createModeSetRequestMessage
is_mode_set_request = isModeSetRequest
is_structured_protocol_message = isStructuredProtocolMessage
mark_messages_as_read_by_predicate = markMessagesAsReadByPredicate
get_last_peer_dm_summary = getLastPeerDmSummary
