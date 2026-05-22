"""Remote session manager — mirrors src/remote/RemoteSessionManager.ts.

Manages a remote CCR session.  Coordinates:
- WebSocket subscription for receiving messages from CCR
- HTTP POST for sending user messages to CCR
- Permission request/response flow
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .sessions_websocket import SessionsWebSocket, SessionsWebSocketCallbacks

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Type aliases / helpers
# ---------------------------------------------------------------------------

def _is_sdk_message(message: dict) -> bool:
    """Type guard: True if *message* is an SDKMessage (not a control message)."""
    return message.get("type") not in (
        "control_request",
        "control_response",
        "control_cancel_request",
    )


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class RemotePermissionResponse:
    """Simplified permission result for CCR communication."""
    behavior: str  # 'allow' | 'deny'
    updated_input: Optional[dict] = None  # only when behavior == 'allow'
    message: Optional[str] = None  # only when behavior == 'deny'


@dataclass
class RemoteSessionConfig:
    session_id: str
    get_access_token: Callable[[], str]
    org_uuid: str
    has_initial_prompt: bool = False
    viewer_only: bool = False


@dataclass
class RemoteSessionCallbacks:
    """Callbacks for RemoteSessionManager events."""
    on_message: Callable[[dict], None]
    """Called when an SDKMessage is received from the session."""
    on_permission_request: Callable[[dict, str], None]
    """Called when a permission request is received from CCR."""
    on_permission_cancelled: Optional[Callable[[str, Optional[str]], None]] = None
    """Called when the server cancels a pending permission request."""
    on_connected: Optional[Callable[[], None]] = None
    """Called when connection is established."""
    on_disconnected: Optional[Callable[[], None]] = None
    """Called when connection is lost and cannot be restored."""
    on_reconnecting: Optional[Callable[[], None]] = None
    """Called on transient WS drop while reconnect backoff is in progress."""
    on_error: Optional[Callable[[Exception], None]] = None
    """Called on error."""


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class RemoteSessionManager:
    """Manages a remote CCR session."""

    def __init__(
        self,
        config: RemoteSessionConfig,
        callbacks: RemoteSessionCallbacks,
    ) -> None:
        self._config = config
        self._callbacks = callbacks
        self._websocket: Optional[SessionsWebSocket] = None
        self._pending_permission_requests: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Connect to the remote session via WebSocket."""
        log.debug(
            "[RemoteSessionManager] Connecting to session %s",
            self._config.session_id,
        )

        ws_callbacks = SessionsWebSocketCallbacks(
            on_message=lambda msg: self._handle_message(msg),
            on_connected=self._on_ws_connected,
            on_close=self._on_ws_close,
            on_reconnecting=self._on_ws_reconnecting,
            on_error=self._on_ws_error,
        )

        self._websocket = SessionsWebSocket(
            session_id=self._config.session_id,
            org_uuid=self._config.org_uuid,
            get_access_token=self._config.get_access_token,
            callbacks=ws_callbacks,
        )

        import asyncio
        asyncio.ensure_future(self._websocket.connect())

    async def send_message(
        self,
        content: Any,
        opts: Optional[dict] = None,
    ) -> bool:
        """Send a user message to the remote session via HTTP POST."""
        log.debug(
            "[RemoteSessionManager] Sending message to session %s",
            self._config.session_id,
        )
        try:
            from ..utils.teleport.api import send_event_to_remote_session
            uuid = (opts or {}).get("uuid")
            success = await send_event_to_remote_session(
                self._config.session_id, content, uuid=uuid
            )
        except (ImportError, Exception) as exc:
            log.error(
                "[RemoteSessionManager] Failed to send message to session %s: %s",
                self._config.session_id,
                exc,
            )
            return False

        if not success:
            log.error(
                "[RemoteSessionManager] Failed to send message to session %s",
                self._config.session_id,
            )
        return success

    def respond_to_permission_request(
        self,
        request_id: str,
        result: RemotePermissionResponse,
    ) -> None:
        """Respond to a permission request from CCR."""
        pending_request = self._pending_permission_requests.get(request_id)
        if pending_request is None:
            log.error(
                "[RemoteSessionManager] No pending permission request with ID: %s",
                request_id,
            )
            return

        del self._pending_permission_requests[request_id]

        if result.behavior == "allow":
            response_body = {
                "behavior": result.behavior,
                "updatedInput": result.updated_input,
            }
        else:
            response_body = {
                "behavior": result.behavior,
                "message": result.message,
            }

        response = {
            "type": "control_response",
            "response": {
                "subtype": "success",
                "request_id": request_id,
                "response": response_body,
            },
        }

        log.debug(
            "[RemoteSessionManager] Sending permission response: %s",
            result.behavior,
        )

        if self._websocket:
            self._websocket.send_control_response(response)

    def is_connected(self) -> bool:
        """Check if connected to the remote session."""
        return self._websocket.is_connected() if self._websocket else False

    def cancel_session(self) -> None:
        """Send an interrupt signal to cancel the current request."""
        log.debug("[RemoteSessionManager] Sending interrupt signal")
        if self._websocket:
            self._websocket.send_control_request({"subtype": "interrupt"})

    def get_session_id(self) -> str:
        """Get the session ID."""
        return self._config.session_id

    def disconnect(self) -> None:
        """Disconnect from the remote session."""
        log.debug("[RemoteSessionManager] Disconnecting")
        if self._websocket:
            self._websocket.close()
            self._websocket = None
        self._pending_permission_requests.clear()

    def reconnect(self) -> None:
        """Force reconnect the WebSocket."""
        log.debug("[RemoteSessionManager] Reconnecting WebSocket")
        if self._websocket:
            self._websocket.reconnect()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _handle_message(self, message: dict) -> None:
        """Handle messages from WebSocket."""
        msg_type = message.get("type", "")

        if msg_type == "control_request":
            self._handle_control_request(message)
            return

        if msg_type == "control_cancel_request":
            request_id = message.get("request_id", "")
            pending_request = self._pending_permission_requests.get(request_id)
            log.debug(
                "[RemoteSessionManager] Permission request cancelled: %s", request_id
            )
            self._pending_permission_requests.pop(request_id, None)
            if self._callbacks.on_permission_cancelled:
                tool_use_id = (
                    pending_request.get("tool_use_id") if pending_request else None
                )
                self._callbacks.on_permission_cancelled(request_id, tool_use_id)
            return

        if msg_type == "control_response":
            log.debug("[RemoteSessionManager] Received control response")
            return

        if _is_sdk_message(message):
            self._callbacks.on_message(message)

    def _handle_control_request(self, request: dict) -> None:
        """Handle control requests from CCR (e.g., permission requests)."""
        request_id = request.get("request_id", "")
        inner = request.get("request", {})

        if inner.get("subtype") == "can_use_tool":
            log.debug(
                "[RemoteSessionManager] Permission request for tool: %s",
                inner.get("tool_name"),
            )
            self._pending_permission_requests[request_id] = inner
            self._callbacks.on_permission_request(inner, request_id)
        else:
            log.debug(
                "[RemoteSessionManager] Unsupported control request subtype: %s",
                inner.get("subtype"),
            )
            error_response = {
                "type": "control_response",
                "response": {
                    "subtype": "error",
                    "request_id": request_id,
                    "error": f"Unsupported control request subtype: {inner.get('subtype')}",
                },
            }
            if self._websocket:
                self._websocket.send_control_response(error_response)

    def _on_ws_connected(self) -> None:
        log.debug("[RemoteSessionManager] Connected")
        if self._callbacks.on_connected:
            self._callbacks.on_connected()

    def _on_ws_close(self) -> None:
        log.debug("[RemoteSessionManager] Disconnected")
        if self._callbacks.on_disconnected:
            self._callbacks.on_disconnected()

    def _on_ws_reconnecting(self) -> None:
        log.debug("[RemoteSessionManager] Reconnecting")
        if self._callbacks.on_reconnecting:
            self._callbacks.on_reconnecting()

    def _on_ws_error(self, error: Exception) -> None:
        log.error("[RemoteSessionManager] Error: %s", error)
        if self._callbacks.on_error:
            self._callbacks.on_error(error)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_remote_session_config(
    session_id: str,
    get_access_token: Callable[[], str],
    org_uuid: str,
    has_initial_prompt: bool = False,
    viewer_only: bool = False,
) -> RemoteSessionConfig:
    """Create a remote session config."""
    return RemoteSessionConfig(
        session_id=session_id,
        get_access_token=get_access_token,
        org_uuid=org_uuid,
        has_initial_prompt=has_initial_prompt,
        viewer_only=viewer_only,
    )
