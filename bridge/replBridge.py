"""Port of src/bridge/replBridge.ts.

Bridge core: environment/session bootstrap plus transport handle setup.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Literal, Optional, Set

from .types import BridgeConfig, SessionActivity

BridgeState = Literal["ready", "connected", "reconnecting", "failed"]


class ReplBridgeHandle:
    """Handle for an active bridge session (REPL mode)."""

    bridgeSessionId: str
    environmentId: str
    sessionIngressUrl: str

    def writeMessages(self, messages: List[Any]) -> None:
        raise NotImplementedError

    def writeSdkMessages(self, messages: List[Any]) -> None:
        raise NotImplementedError

    def sendControlRequest(self, request: Any) -> None:
        raise NotImplementedError

    def sendControlResponse(self, response: Any) -> None:
        raise NotImplementedError

    def sendControlCancelRequest(self, request_id: str) -> None:
        raise NotImplementedError

    def sendResult(self) -> None:
        raise NotImplementedError

    async def teardown(self) -> None:
        raise NotImplementedError


class BridgeCoreHandle(ReplBridgeHandle):
    """Superset of ReplBridgeHandle — adds SSE sequence number access."""

    def getSSESequenceNum(self) -> int:
        return 0


async def initBridgeCore(
    directory: str,
    machine_name: str,
    branch: str,
    git_repo_url: Optional[str],
    title: str,
    base_url: str,
    session_ingress_url: str,
    worker_type: str,
    get_access_token: Callable[[], Optional[str]],
    create_session: Callable,
    archive_session: Callable,
    get_current_title: Optional[Callable[[], str]] = None,
    to_sdk_messages: Optional[Callable] = None,
    on_auth_401: Optional[Callable] = None,
    get_poll_interval_config: Optional[Callable] = None,
    initial_history_cap: int = 200,
    initial_messages: Optional[List[Any]] = None,
    previously_flushed_uuids: Optional[Set[str]] = None,
    on_inbound_message: Optional[Callable] = None,
    on_permission_response: Optional[Callable] = None,
    on_interrupt: Optional[Callable] = None,
    on_set_model: Optional[Callable] = None,
    on_set_max_thinking_tokens: Optional[Callable] = None,
    on_set_permission_mode: Optional[Callable] = None,
    on_state_change: Optional[Callable] = None,
    on_user_message: Optional[Callable] = None,
    perpetual: bool = False,
    initial_sse_sequence_num: int = 0,
) -> Optional[BridgeCoreHandle]:
    """Bootstrap-free core for REPL bridge initialization.

    The env-based TypeScript path is substantially larger than the current
    Python runtime. Until the full environments poller is ported, route the
    fallback REPL path through the functional env-less bridge core so callers
    receive a live handle instead of a hard stub.
    """
    if to_sdk_messages is None:
        raise ValueError("to_sdk_messages is required for initBridgeCore")

    try:
        from ..services.oauth.client import get_organization_uuid
        from ..utils.debug import log_for_debugging

        org_uuid = await get_organization_uuid()
        if not org_uuid:
            log_for_debugging("[bridge:core] Could not resolve org UUID for bridge init")
            on_state_change and on_state_change("failed", "/login")
            return None

        from .remoteBridgeCore import initEnvLessBridgeCore

        handle = await initEnvLessBridgeCore(
            base_url=base_url,
            org_uuid=org_uuid,
            title=get_current_title() if get_current_title else title,
            get_access_token=get_access_token,
            on_auth_401=on_auth_401,
            to_sdk_messages=to_sdk_messages,
            initial_history_cap=initial_history_cap,
            initial_messages=initial_messages,
            on_inbound_message=on_inbound_message,
            on_user_message=on_user_message,
            on_permission_response=on_permission_response,
            on_interrupt=on_interrupt,
            on_set_model=on_set_model,
            on_set_max_thinking_tokens=on_set_max_thinking_tokens,
            on_set_permission_mode=on_set_permission_mode,
            on_state_change=on_state_change,
            outbound_only=False,
            tags=None,
        )
        if handle is None:
            return None

        class _BridgeCoreHandle(BridgeCoreHandle):
            bridgeSessionId = handle.bridgeSessionId
            environmentId = getattr(handle, "environmentId", "")
            sessionIngressUrl = getattr(handle, "sessionIngressUrl", "")

            def writeMessages(self, messages: List[Any]) -> None:
                handle.writeMessages(messages)

            def writeSdkMessages(self, messages: List[Any]) -> None:
                handle.writeSdkMessages(messages)

            def sendControlRequest(self, request: Any) -> None:
                handle.sendControlRequest(request)

            def sendControlResponse(self, response: Any) -> None:
                handle.sendControlResponse(response)

            def sendControlCancelRequest(self, request_id: str) -> None:
                handle.sendControlCancelRequest(request_id)

            def sendResult(self) -> None:
                handle.sendResult()

            async def teardown(self) -> None:
                await handle.teardown()

            def getSSESequenceNum(self) -> int:
                getter = getattr(handle, "getSSESequenceNum", None)
                if callable(getter):
                    try:
                        return int(getter())
                    except Exception:
                        return 0
                return 0

        return _BridgeCoreHandle()
    except Exception as err:
        try:
            from ..utils.debug import log_for_debugging

            log_for_debugging(f"[bridge:core] initBridgeCore failed: {err}", level="error")
        except Exception:
            pass
        on_state_change and on_state_change("failed", str(err))
        return None
