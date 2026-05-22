"""Port of src/bridge/remoteBridgeCore.ts.

Env-less Remote Control bridge core.

"Env-less" = no Environments API layer. Connects directly to the session-ingress
layer without the Environments API work-dispatch layer.
"""
from __future__ import annotations

import asyncio
import inspect
import random
from typing import Any, Callable, Dict, List, Optional

import httpx

from .bridgeMessaging import (
    BoundedUUIDSet,
    extractTitleText,
    handleIngressMessage,
    handleServerControlRequest,
    isEligibleBridgeMessage,
    makeResultMessage,
)
from .codeSessionApi import RemoteCredentials, createCodeSession, fetchRemoteCredentials
from .envLessBridgeConfig import EnvLessBridgeConfig, getEnvLessBridgeConfig
from .flushGate import FlushGate
from .jwtUtils import createTokenRefreshScheduler
from .replBridge import ReplBridgeHandle
from .replBridgeTransport import createV2ReplTransport
from .sessionIdCompat import toCompatSessionId
from .workSecret import buildCCRv2SdkUrl


class EnvLessBridgeParams:
    """Parameters for initEnvLessBridgeCore."""
    base_url: str
    org_uuid: str
    title: str
    get_access_token: Callable[[], Optional[str]]
    on_auth_401: Optional[Callable]
    to_sdk_messages: Optional[Callable]
    initial_history_cap: int
    initial_messages: Optional[List[Any]]
    on_inbound_message: Optional[Callable]
    on_user_message: Optional[Callable]
    on_permission_response: Optional[Callable]
    on_interrupt: Optional[Callable]
    on_set_model: Optional[Callable]
    on_set_max_thinking_tokens: Optional[Callable]
    on_set_permission_mode: Optional[Callable]
    on_state_change: Optional[Callable]
    outbound_only: bool
    tags: Optional[List[str]]


async def _invoke_auth_refresh(callback: Callable[..., Any], stale_token: str) -> Any:
    try:
        params = inspect.signature(callback).parameters
        maybe = callback(stale_token) if len(params) >= 1 else callback()
    except (TypeError, ValueError):
        maybe = callback(stale_token)
    if asyncio.iscoroutine(maybe):
        return await maybe
    return maybe


async def initEnvLessBridgeCore(
    base_url: str,
    org_uuid: Optional[str],
    title: str,
    get_access_token: Callable[[], Optional[str]],
    on_auth_401: Optional[Callable] = None,
    to_sdk_messages: Optional[Callable] = None,
    initial_history_cap: int = 200,
    initial_messages: Optional[List[Any]] = None,
    on_inbound_message: Optional[Callable] = None,
    on_user_message: Optional[Callable] = None,
    on_permission_response: Optional[Callable] = None,
    on_interrupt: Optional[Callable] = None,
    on_set_model: Optional[Callable] = None,
    on_set_max_thinking_tokens: Optional[Callable] = None,
    on_set_permission_mode: Optional[Callable] = None,
    on_state_change: Optional[Callable] = None,
    outbound_only: bool = False,
    tags: Optional[List[str]] = None,
) -> Optional[ReplBridgeHandle]:
    """Env-less bridge: POST /bridge -> worker_jwt -> SSE transport."""
    if to_sdk_messages is None:
        raise ValueError("to_sdk_messages is required for initEnvLessBridgeCore")

    cfg = await getEnvLessBridgeConfig()
    access_token = get_access_token()
    if not access_token:
        try:
            from ..utils.debug import log_for_debugging
            log_for_debugging("[bridge:remote] No OAuth token for env-less bridge")
        except Exception:
            pass
        return None

    session_id = await _with_retry(
        lambda: createCodeSession(base_url, access_token, title, cfg["http_timeout_ms"], tags),
        "createCodeSession",
        cfg,
    )
    if not session_id:
        on_state_change and on_state_change("failed", "Session creation failed")
        return None

    credentials = await _with_retry(
        lambda: fetchRemoteCredentials(session_id, base_url, access_token, cfg["http_timeout_ms"]),
        "fetchRemoteCredentials",
        cfg,
    )
    if not credentials:
        on_state_change and on_state_change("failed", "Remote credentials fetch failed")
        await _archive_session(session_id, base_url, access_token, org_uuid, cfg["teardown_archive_timeout_ms"])
        return None

    transport = await createV2ReplTransport(
        session_url=buildCCRv2SdkUrl(credentials["api_base_url"], session_id),
        ingress_token=credentials["worker_jwt"],
        session_id=session_id,
        epoch=credentials["worker_epoch"],
        heartbeat_interval_ms=cfg["heartbeat_interval_ms"],
        heartbeat_jitter_fraction=cfg["heartbeat_jitter_fraction"],
        outbound_only=outbound_only,
        get_auth_token=lambda: credentials["worker_jwt"],
    )

    recent_posted_uuids = BoundedUUIDSet(cfg["uuid_dedup_buffer_size"])
    initial_message_uuids: set[str] = set()
    if initial_messages:
        for msg in initial_messages:
            msg_uuid = getattr(msg, "uuid", None) if not isinstance(msg, dict) else msg.get("uuid")
            if isinstance(msg_uuid, str):
                initial_message_uuids.add(msg_uuid)
                recent_posted_uuids.add(msg_uuid)
    recent_inbound_uuids = BoundedUUIDSet(cfg["uuid_dedup_buffer_size"])
    flush_gate: FlushGate[Any] = FlushGate()
    if initial_messages:
        flush_gate.start()

    torn_down = False
    auth_recovery_in_flight = False
    initial_flush_done = False
    user_message_callback_done = on_user_message is None
    connect_cause = "initial"
    connect_deadline: Optional[asyncio.TimerHandle] = None

    def _clear_connect_deadline() -> None:
        nonlocal connect_deadline
        if connect_deadline is not None:
            connect_deadline.cancel()
            connect_deadline = None

    async def flush_history(messages: List[Any]) -> None:
        eligible = [m for m in messages if isEligibleBridgeMessage(m)]
        capped = eligible[-initial_history_cap:] if initial_history_cap > 0 else eligible
        if not capped:
            return
        events = [{**event, "session_id": session_id} for event in to_sdk_messages(capped)]
        if any((m.get("type") if isinstance(m, dict) else getattr(m, "type", None)) == "user" for m in capped):
            transport.reportState("running")
        await transport.writeBatch(events)

    def drain_flush_gate() -> None:
        queued = flush_gate.end()
        if not queued:
            return
        for msg in queued:
            msg_uuid = msg.get("uuid") if isinstance(msg, dict) else getattr(msg, "uuid", None)
            if isinstance(msg_uuid, str):
                recent_posted_uuids.add(msg_uuid)
        events = [{**event, "session_id": session_id} for event in to_sdk_messages(queued)]
        if any((m.get("type") if isinstance(m, dict) else getattr(m, "type", None)) == "user" for m in queued):
            transport.reportState("running")
        asyncio.ensure_future(transport.writeBatch(events))

    async def rebuild_transport(fresh: RemoteCredentials, cause: str) -> None:
        nonlocal transport, connect_cause
        connect_cause = cause
        flush_gate.start()
        seq = transport.getLastSequenceNum()
        transport.close()
        transport = await createV2ReplTransport(
            session_url=buildCCRv2SdkUrl(fresh["api_base_url"], session_id),
            ingress_token=fresh["worker_jwt"],
            session_id=session_id,
            epoch=fresh["worker_epoch"],
            heartbeat_interval_ms=cfg["heartbeat_interval_ms"],
            heartbeat_jitter_fraction=cfg["heartbeat_jitter_fraction"],
            initial_sequence_num=seq,
            outbound_only=outbound_only,
            get_auth_token=lambda: fresh["worker_jwt"],
        )
        wire_transport_callbacks()
        transport.connect()
        _arm_connect_timeout()
        refresh_scheduler["scheduleFromExpiresIn"](session_id, fresh["expires_in"])
        drain_flush_gate()

    async def recover_from_auth_failure() -> None:
        nonlocal auth_recovery_in_flight, initial_flush_done
        if auth_recovery_in_flight or torn_down:
            return
        auth_recovery_in_flight = True
        on_state_change and on_state_change("reconnecting", "JWT expired - refreshing")
        try:
            stale = get_access_token() or ""
            if on_auth_401 is not None:
                await _invoke_auth_refresh(on_auth_401, stale)
            oauth_token = get_access_token() or stale
            if not oauth_token:
                on_state_change and on_state_change("failed", "JWT refresh failed")
                return
            fresh = await _with_retry(
                lambda: fetchRemoteCredentials(session_id, base_url, oauth_token, cfg["http_timeout_ms"]),
                "fetchRemoteCredentials(recovery)",
                cfg,
            )
            if not fresh:
                on_state_change and on_state_change("failed", "JWT refresh failed")
                return
            initial_flush_done = False
            await rebuild_transport(fresh, "auth_401_recovery")
        finally:
            auth_recovery_in_flight = False

    def _arm_connect_timeout() -> None:
        loop = asyncio.get_event_loop()
        _clear_connect_deadline()
        connect_deadline = loop.call_later(
            cfg["connect_timeout_ms"] / 1000.0,
            lambda: None if torn_down else on_state_change and on_state_change("failed", f"Transport connect timeout ({connect_cause})"),
        )

    def wire_transport_callbacks() -> None:
        def _on_connect() -> None:
            nonlocal initial_flush_done
            _clear_connect_deadline()
            if not initial_flush_done and initial_messages:
                initial_flush_done = True
                async def _flush() -> None:
                    await flush_history(initial_messages)
                    if not torn_down and not auth_recovery_in_flight:
                        drain_flush_gate()
                        on_state_change and on_state_change("connected")
                asyncio.ensure_future(_flush())
            elif not flush_gate.active:
                on_state_change and on_state_change("connected")

        def _permission_response(response: Any) -> None:
            transport.reportState("running")
            if on_permission_response:
                result = on_permission_response(response)
                if asyncio.iscoroutine(result):
                    asyncio.ensure_future(result)

        def _control_request(request: Any) -> None:
            handleServerControlRequest(
                request,
                transport,
                session_id,
                outbound_only=outbound_only,
                on_interrupt=on_interrupt,
                on_set_model=on_set_model,
                on_set_max_thinking_tokens=on_set_max_thinking_tokens,
                on_set_permission_mode=on_set_permission_mode,
            )

        def _on_data(data: str) -> None:
            handleIngressMessage(
                data,
                recent_posted_uuids,
                recent_inbound_uuids,
                on_inbound_message,
                _permission_response if on_permission_response else None,
                _control_request,
            )

        def _on_close(code: Optional[int] = None) -> None:
            _clear_connect_deadline()
            if torn_down:
                return
            if code == 401 and not auth_recovery_in_flight:
                asyncio.ensure_future(recover_from_auth_failure())
                return
            on_state_change and on_state_change("failed", f"Transport closed (code {code})")

        transport.setOnConnect(_on_connect)
        transport.setOnData(_on_data)
        transport.setOnClose(_on_close)

    async def teardown_impl() -> None:
        nonlocal torn_down
        if torn_down:
            return
        torn_down = True
        refresh_scheduler["cancelAll"]()
        _clear_connect_deadline()
        flush_gate.drop()
        transport.reportState("idle")
        asyncio.ensure_future(transport.write(makeResultMessage(session_id)))
        token = get_access_token()
        status = await _archive_session(session_id, base_url, token, org_uuid, cfg["teardown_archive_timeout_ms"])
        if status == 401 and on_auth_401 is not None:
            try:
                await _invoke_auth_refresh(on_auth_401, token or "")
                token = get_access_token()
                await _archive_session(session_id, base_url, token, org_uuid, cfg["teardown_archive_timeout_ms"])
            except Exception:
                pass
        transport.close()

    refresh_scheduler = createTokenRefreshScheduler(
        get_access_token=get_access_token,
        on_refresh=lambda _sid, oauth_token: asyncio.ensure_future(
            _refresh_from_scheduler(oauth_token)
        ),
        label="remote",
        refresh_buffer_ms=cfg["token_refresh_buffer_ms"],
    )

    async def _refresh_from_scheduler(oauth_token: str) -> None:
        nonlocal auth_recovery_in_flight
        if auth_recovery_in_flight or torn_down:
            return
        auth_recovery_in_flight = True
        try:
            fresh = await _with_retry(
                lambda: fetchRemoteCredentials(session_id, base_url, oauth_token, cfg["http_timeout_ms"]),
                "fetchRemoteCredentials(refresh)",
                cfg,
            )
            if fresh:
                await rebuild_transport(fresh, "proactive_refresh")
        finally:
            auth_recovery_in_flight = False

    refresh_scheduler["scheduleFromExpiresIn"](session_id, credentials["expires_in"])
    wire_transport_callbacks()
    transport.connect()
    _arm_connect_timeout()
    on_state_change and on_state_change("ready")

    def write_messages(messages: List[Any]) -> None:
        nonlocal user_message_callback_done
        filtered: List[Any] = []
        for msg in messages:
            msg_uuid = msg.get("uuid") if isinstance(msg, dict) else getattr(msg, "uuid", None)
            if not isEligibleBridgeMessage(msg):
                continue
            if isinstance(msg_uuid, str) and (msg_uuid in initial_message_uuids or recent_posted_uuids.has(msg_uuid)):
                continue
            filtered.append(msg)
        if not filtered:
            return

        if not user_message_callback_done and on_user_message is not None:
            for msg in filtered:
                text = extractTitleText(msg)
                if text is not None and on_user_message(text, session_id):
                    user_message_callback_done = True
                    break

        if flush_gate.enqueue(*filtered):
            return

        for msg in filtered:
            msg_uuid = msg.get("uuid") if isinstance(msg, dict) else getattr(msg, "uuid", None)
            if isinstance(msg_uuid, str):
                recent_posted_uuids.add(msg_uuid)
        events = [{**event, "session_id": session_id} for event in to_sdk_messages(filtered)]
        if any((m.get("type") if isinstance(m, dict) else getattr(m, "type", None)) == "user" for m in filtered):
            transport.reportState("running")
        asyncio.ensure_future(transport.writeBatch(events))

    def write_sdk_messages(messages: List[Dict[str, Any]]) -> None:
        filtered: List[Dict[str, Any]] = []
        for msg in messages:
            msg_uuid = msg.get("uuid")
            if isinstance(msg_uuid, str) and recent_posted_uuids.has(msg_uuid):
                continue
            filtered.append(msg)
            if isinstance(msg_uuid, str):
                recent_posted_uuids.add(msg_uuid)
        if not filtered:
            return
        asyncio.ensure_future(transport.writeBatch([{**msg, "session_id": session_id} for msg in filtered]))

    def send_control_request(request: Dict[str, Any]) -> None:
        if auth_recovery_in_flight:
            return
        event = {**request, "session_id": session_id}
        if request.get("request", {}).get("subtype") == "can_use_tool":
            transport.reportState("requires_action")
        asyncio.ensure_future(transport.write(event))

    def send_control_response(response: Dict[str, Any]) -> None:
        if auth_recovery_in_flight:
            return
        transport.reportState("running")
        asyncio.ensure_future(transport.write({**response, "session_id": session_id}))

    def send_control_cancel_request(request_id: str) -> None:
        if auth_recovery_in_flight:
            return
        transport.reportState("running")
        asyncio.ensure_future(
            transport.write({"type": "control_cancel_request", "request_id": request_id, "session_id": session_id})
        )

    def send_result() -> None:
        if auth_recovery_in_flight:
            return
        transport.reportState("idle")
        asyncio.ensure_future(transport.write(makeResultMessage(session_id)))

    try:
        from ..utils.cleanupRegistry import register_cleanup
        unregister = register_cleanup(teardown_impl)
    except Exception:
        unregister = None

    class _Handle:
        bridgeSessionId = session_id
        environmentId = ""
        sessionIngressUrl = credentials["api_base_url"]

        def writeMessages(self, messages: List[Any]) -> None:
            write_messages(messages)

        def writeSdkMessages(self, messages: List[Any]) -> None:
            write_sdk_messages(messages)

        def sendControlRequest(self, request: Any) -> None:
            send_control_request(request)

        def sendControlResponse(self, response: Any) -> None:
            send_control_response(response)

        def sendControlCancelRequest(self, request_id: str) -> None:
            send_control_cancel_request(request_id)

        def sendResult(self) -> None:
            send_result()

        async def teardown(self) -> None:
            if unregister:
                try:
                    result = unregister()
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    pass
            await teardown_impl()

    return _Handle()


async def _with_retry(
    fn: Callable[[], Any],
    label: str,
    cfg: EnvLessBridgeConfig,
) -> Any:
    max_attempts = cfg["init_retry_max_attempts"]
    for attempt in range(1, max_attempts + 1):
        result = await fn()
        if result is not None:
            return result
        if attempt < max_attempts:
            base = cfg["init_retry_base_delay_ms"] * (2 ** (attempt - 1))
            jitter = base * cfg["init_retry_jitter_fraction"] * (2 * random.random() - 1)
            delay_ms = min(base + jitter, cfg["init_retry_max_delay_ms"])
            await asyncio.sleep(delay_ms / 1000.0)
    return None


async def _archive_session(
    session_id: str,
    base_url: str,
    access_token: Optional[str],
    org_uuid: Optional[str],
    timeout_ms: int,
) -> int | str:
    if not access_token:
        return "no_token"
    compat_id = toCompatSessionId(session_id)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "ccr-byoc-2025-07-29",
    }
    if org_uuid:
        headers["x-organization-uuid"] = org_uuid
    try:
        async with httpx.AsyncClient(timeout=timeout_ms / 1000.0) as client:
            response = await client.post(f"{base_url}/v1/sessions/{compat_id}/archive", json={}, headers=headers)
        return response.status_code
    except httpx.TimeoutException:
        return "timeout"
    except Exception:
        return "error"
