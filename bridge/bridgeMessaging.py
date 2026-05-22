"""Port of src/bridge/bridgeMessaging.ts

Shared transport-layer helpers for bridge message handling.
"""
from __future__ import annotations

import uuid as _uuid
from typing import Any, Callable, Dict, List, Optional


# ─── Type guards ─────────────────────────────────────────────────────────────

def isSDKMessage(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and "type" in value
        and isinstance(value["type"], str)
    )


def isSDKControlResponse(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("type") == "control_response"
        and "response" in value
    )


def isSDKControlRequest(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("type") == "control_request"
        and "request_id" in value
        and "request" in value
    )


def isEligibleBridgeMessage(m: Dict[str, Any]) -> bool:
    """True for message types that should be forwarded to the bridge transport."""
    if m.get("type") in ("user", "assistant") and m.get("isVirtual"):
        return False
    return (
        m.get("type") in ("user", "assistant")
        or (m.get("type") == "system" and m.get("subtype") == "local_command")
    )


def extractTitleText(m: Dict[str, Any]) -> Optional[str]:
    """Extract title-worthy text from a Message."""
    if m.get("type") != "user" or m.get("isMeta") or m.get("toolUseResult") or m.get("isCompactSummary"):
        return None
    origin = m.get("origin")
    if origin and isinstance(origin, dict) and origin.get("kind") != "human":
        return None
    content = m.get("message", {}).get("content")
    raw: Optional[str] = None
    if isinstance(content, str):
        raw = content
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                raw = block.get("text")
                break
    if not raw:
        return None
    try:
        from ..utils.display_tags import strip_display_tags_allow_empty
        clean = strip_display_tags_allow_empty(raw)
    except Exception:
        clean = raw
    return clean or None


# ─── Ingress routing ─────────────────────────────────────────────────────────

def handleIngressMessage(
    data: str,
    recent_posted_uuids: "BoundedUUIDSet",
    recent_inbound_uuids: "BoundedUUIDSet",
    on_inbound_message: Optional[Callable],
    on_permission_response: Optional[Callable] = None,
    on_control_request: Optional[Callable] = None,
) -> None:
    """Parse an ingress WebSocket message and route it to the appropriate handler."""
    import json
    try:
        try:
            from ..utils.control_message_compat import normalize_control_message_keys
            parsed = normalize_control_message_keys(json.loads(data))
        except Exception:
            parsed = json.loads(data)

        if isSDKControlResponse(parsed):
            try:
                from ..utils.debug import log_for_debugging
                log_for_debugging("[bridge:repl] Ingress message type=control_response")
            except Exception:
                pass
            if on_permission_response:
                on_permission_response(parsed)
            return

        if isSDKControlRequest(parsed):
            try:
                from ..utils.debug import log_for_debugging
                log_for_debugging(f"[bridge:repl] Inbound control_request subtype={parsed['request'].get('subtype')}")
            except Exception:
                pass
            if on_control_request:
                on_control_request(parsed)
            return

        if not isSDKMessage(parsed):
            return

        uid = parsed.get("uuid") if isinstance(parsed.get("uuid"), str) else None

        if uid and recent_posted_uuids.has(uid):
            try:
                from ..utils.debug import log_for_debugging
                log_for_debugging(f"[bridge:repl] Ignoring echo: type={parsed['type']} uuid={uid}")
            except Exception:
                pass
            return

        if uid and recent_inbound_uuids.has(uid):
            try:
                from ..utils.debug import log_for_debugging
                log_for_debugging(f"[bridge:repl] Ignoring re-delivered inbound: type={parsed['type']} uuid={uid}")
            except Exception:
                pass
            return

        try:
            from ..utils.debug import log_for_debugging
            log_for_debugging(f"[bridge:repl] Ingress message type={parsed['type']}" + (f" uuid={uid}" if uid else ""))
        except Exception:
            pass

        if parsed.get("type") == "user":
            if uid:
                recent_inbound_uuids.add(uid)
            try:
                from ..services.analytics import log_event
                log_event("tengu_bridge_message_received", {"is_repl": True})
            except Exception:
                pass
            if on_inbound_message:
                import asyncio
                result = on_inbound_message(parsed)
                if asyncio.iscoroutine(result):
                    asyncio.ensure_future(result)
    except Exception as err:
        try:
            from ..utils.debug import log_for_debugging
            log_for_debugging(f"[bridge:repl] Failed to parse ingress message: {err}")
        except Exception:
            pass


# ─── Server-initiated control requests ───────────────────────────────────────

OUTBOUND_ONLY_ERROR = (
    "This session is outbound-only. Enable Remote Control locally to allow inbound control."
)


def handleServerControlRequest(
    request: Dict[str, Any],
    transport: Any,
    session_id: str,
    outbound_only: bool = False,
    on_interrupt: Optional[Callable] = None,
    on_set_model: Optional[Callable] = None,
    on_set_max_thinking_tokens: Optional[Callable] = None,
    on_set_permission_mode: Optional[Callable] = None,
) -> None:
    """Respond to inbound control_request messages from the server."""
    import os

    if not transport:
        try:
            from ..utils.debug import log_for_debugging
            log_for_debugging("[bridge:repl] Cannot respond to control_request: transport not configured")
        except Exception:
            pass
        return

    req = request.get("request", {})
    subtype = req.get("subtype")
    request_id = request.get("request_id")

    def _send(response: Dict[str, Any]) -> None:
        event = {**response, "session_id": session_id}
        import asyncio
        result = transport.write(event)
        if asyncio.iscoroutine(result):
            asyncio.ensure_future(result)

    # Outbound-only mode: reject mutable requests (but allow initialize)
    if outbound_only and subtype != "initialize":
        _send({
            "type": "control_response",
            "response": {
                "subtype": "error",
                "request_id": request_id,
                "error": OUTBOUND_ONLY_ERROR,
            },
        })
        try:
            from ..utils.debug import log_for_debugging
            log_for_debugging(f"[bridge:repl] Rejected {subtype} (outbound-only) request_id={request_id}")
        except Exception:
            pass
        return

    response: Dict[str, Any]

    if subtype == "initialize":
        response = {
            "type": "control_response",
            "response": {
                "subtype": "success",
                "request_id": request_id,
                "response": {
                    "commands": [],
                    "output_style": "normal",
                    "available_output_styles": ["normal"],
                    "models": [],
                    "account": {},
                    "pid": os.getpid(),
                },
            },
        }
    elif subtype == "set_model":
        if on_set_model:
            on_set_model(req.get("model"))
        response = {"type": "control_response", "response": {"subtype": "success", "request_id": request_id}}
    elif subtype == "set_max_thinking_tokens":
        if on_set_max_thinking_tokens:
            on_set_max_thinking_tokens(req.get("max_thinking_tokens"))
        response = {"type": "control_response", "response": {"subtype": "success", "request_id": request_id}}
    elif subtype == "set_permission_mode":
        verdict = on_set_permission_mode(req.get("mode")) if on_set_permission_mode else {
            "ok": False,
            "error": "set_permission_mode is not supported in this context (onSetPermissionMode callback not registered)",
        }
        if verdict.get("ok"):
            response = {"type": "control_response", "response": {"subtype": "success", "request_id": request_id}}
        else:
            response = {"type": "control_response", "response": {"subtype": "error", "request_id": request_id, "error": verdict.get("error", "unknown error")}}
    elif subtype == "interrupt":
        if on_interrupt:
            on_interrupt()
        response = {"type": "control_response", "response": {"subtype": "success", "request_id": request_id}}
    else:
        response = {"type": "control_response", "response": {"subtype": "error", "request_id": request_id, "error": f"REPL bridge does not handle control_request subtype: {subtype}"}}

    _send(response)
    try:
        from ..utils.debug import log_for_debugging
        log_for_debugging(f"[bridge:repl] Sent control_response for {subtype} request_id={request_id} result={response['response']['subtype']}")
    except Exception:
        pass


# ─── Result message ─────────────────────────────────────────────────────────

def makeResultMessage(session_id: str) -> Dict[str, Any]:
    """Build a minimal SDKResultSuccess message for session archival."""
    empty_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    return {
        "type": "result",
        "subtype": "success",
        "duration_ms": 0,
        "duration_api_ms": 0,
        "is_error": False,
        "num_turns": 0,
        "result": "",
        "stop_reason": None,
        "total_cost_usd": 0,
        "usage": empty_usage,
        "modelUsage": {},
        "permission_denials": [],
        "session_id": session_id,
        "uuid": str(_uuid.uuid4()),
    }


# ─── BoundedUUIDSet ─────────────────────────────────────────────────────────

class BoundedUUIDSet:
    """FIFO-bounded set backed by a circular buffer for echo-dedup."""

    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._ring: List[Optional[str]] = [None] * capacity
        self._set: set = set()
        self._write_idx = 0

    def add(self, uid: str) -> None:
        if uid in self._set:
            return
        evicted = self._ring[self._write_idx]
        if evicted is not None:
            self._set.discard(evicted)
        self._ring[self._write_idx] = uid
        self._set.add(uid)
        self._write_idx = (self._write_idx + 1) % self._capacity

    def has(self, uid: str) -> bool:
        return uid in self._set

    def clear(self) -> None:
        self._set.clear()
        self._ring = [None] * self._capacity
        self._write_idx = 0
