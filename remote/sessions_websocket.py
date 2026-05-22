"""Sessions WebSocket — mirrors src/remote/SessionsWebSocket.ts.

WebSocket client for connecting to CCR sessions via
/v1/sessions/ws/{id}/subscribe.

Protocol:
1. Connect to wss://api.anthropic.com/v1/sessions/ws/{sessionId}/subscribe?organization_uuid=...
2. Auth is sent as Authorization header
3. Receive SDKMessage stream from the session
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
from dataclasses import dataclass
from typing import Callable, Literal, Optional
from uuid import uuid4

log = logging.getLogger(__name__)

RECONNECT_DELAY_S = 2.0
MAX_RECONNECT_ATTEMPTS = 5
PING_INTERVAL_S = 30.0

# Maximum retries for session-not-found (4001).
# During compaction the server may briefly consider the session stale.
MAX_SESSION_NOT_FOUND_RETRIES = 3

# Close codes that indicate a permanent server-side rejection.
PERMANENT_CLOSE_CODES: set[int] = {
    4003,  # unauthorized
}

WebSocketState = Literal["connecting", "connected", "closed"]


def _is_sessions_message(value: object) -> bool:
    """Accept any dict with a string 'type' field."""
    return (
        isinstance(value, dict)
        and "type" in value
        and isinstance(value["type"], str)
    )


@dataclass
class SessionsWebSocketCallbacks:
    on_message: Callable[[dict], None]
    on_close: Optional[Callable[[], None]] = None
    on_error: Optional[Callable[[Exception], None]] = None
    on_connected: Optional[Callable[[], None]] = None
    on_reconnecting: Optional[Callable[[], None]] = None


class SessionsWebSocket:
    """WebSocket client for /v1/sessions/ws/{sessionId}/subscribe."""

    def __init__(
        self,
        session_id: str,
        org_uuid: str,
        get_access_token: Callable[[], str],
        callbacks: SessionsWebSocketCallbacks,
    ) -> None:
        self._session_id = session_id
        self._org_uuid = org_uuid
        self._get_access_token = get_access_token
        self._callbacks = callbacks

        self._ws: Optional[object] = None
        self._state: WebSocketState = "closed"
        self._reconnect_attempts = 0
        self._session_not_found_retries = 0
        self._ping_task: Optional[asyncio.Task] = None
        self._reconnect_timer: Optional[asyncio.TimerHandle] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Connect to the sessions WebSocket endpoint."""
        if self._state == "connecting":
            log.debug("[SessionsWebSocket] Already connecting")
            return

        self._state = "connecting"

        try:
            from ..constants.oauth import get_oauth_config
            base_url = get_oauth_config().base_api_url.replace("https://", "wss://")
        except (ImportError, Exception):
            base_url = "wss://api.anthropic.com"

        url = (
            f"{base_url}/v1/sessions/ws/{self._session_id}/subscribe"
            f"?organization_uuid={self._org_uuid}"
        )
        log.debug("[SessionsWebSocket] Connecting to %s", url)

        access_token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "anthropic-version": "2023-06-01",
        }

        try:
            import websockets  # type: ignore

            async with websockets.connect(
                url, additional_headers=headers
            ) as ws:
                self._ws = ws
                self._state = "connected"
                self._reconnect_attempts = 0
                self._session_not_found_retries = 0
                log.debug(
                    "[SessionsWebSocket] Connection opened, authenticated via headers"
                )
                self._start_ping_task(ws)
                if self._callbacks.on_connected:
                    self._callbacks.on_connected()

                try:
                    async for raw in ws:
                        data = raw if isinstance(raw, str) else raw.decode()
                        self._handle_message(data)
                finally:
                    self._stop_ping_task()

        except Exception as exc:
            log.debug("[SessionsWebSocket] Connection error: %s", exc)
            if self._callbacks.on_error:
                self._callbacks.on_error(exc if isinstance(exc, Exception) else Exception(str(exc)))
            self._handle_close(1006)  # abnormal closure
        finally:
            self._ws = None
            if self._state != "closed":
                self._state = "closed"

    def send_control_response(self, response: dict) -> None:
        """Send a control response back to the session."""
        if self._ws is None or self._state != "connected":
            log.error("[SessionsWebSocket] Cannot send: not connected")
            return
        log.debug("[SessionsWebSocket] Sending control response")
        self._send_json(response)

    def send_control_request(self, request: dict) -> None:
        """Send a control request to the session (e.g., interrupt)."""
        if self._ws is None or self._state != "connected":
            log.error("[SessionsWebSocket] Cannot send: not connected")
            return
        control_request = {
            "type": "control_request",
            "request_id": str(uuid4()),
            "request": request,
        }
        log.debug(
            "[SessionsWebSocket] Sending control request: %s",
            request.get("subtype"),
        )
        self._send_json(control_request)

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._state == "connected"

    def close(self) -> None:
        """Close the WebSocket connection."""
        log.debug("[SessionsWebSocket] Closing connection")
        self._state = "closed"
        self._stop_ping_task()
        self._cancel_reconnect_timer()
        if self._ws is not None:
            asyncio.ensure_future(self._close_ws())

    async def _close_ws(self) -> None:
        ws = self._ws
        self._ws = None
        if ws is not None:
            try:
                await ws.close()  # type: ignore
            except Exception:
                pass

    def reconnect(self) -> None:
        """Force reconnect — closes existing connection and starts a new one."""
        log.debug("[SessionsWebSocket] Force reconnecting")
        self._reconnect_attempts = 0
        self._session_not_found_retries = 0
        self.close()
        loop = asyncio.get_event_loop()
        handle = loop.call_later(0.1, lambda: asyncio.ensure_future(self.connect()))
        self._reconnect_timer = handle

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _handle_message(self, data: str) -> None:
        try:
            message = json.loads(data)
            if _is_sessions_message(message):
                self._callbacks.on_message(message)  # type: ignore[arg-type]
            else:
                log.debug(
                    "[SessionsWebSocket] Ignoring message type: %s",
                    message.get("type", "unknown") if isinstance(message, dict) else "unknown",
                )
        except Exception as exc:
            log.error(
                "[SessionsWebSocket] Failed to parse message: %s", exc
            )

    def _handle_close(self, close_code: int) -> None:
        self._stop_ping_task()

        if self._state == "closed":
            return

        previous_state = self._state
        self._state = "closed"

        if close_code in PERMANENT_CLOSE_CODES:
            log.debug(
                "[SessionsWebSocket] Permanent close code %d, not reconnecting",
                close_code,
            )
            if self._callbacks.on_close:
                self._callbacks.on_close()
            return

        if close_code == 4001:
            self._session_not_found_retries += 1
            if self._session_not_found_retries > MAX_SESSION_NOT_FOUND_RETRIES:
                log.debug(
                    "[SessionsWebSocket] 4001 retry budget exhausted (%d), not reconnecting",
                    MAX_SESSION_NOT_FOUND_RETRIES,
                )
                if self._callbacks.on_close:
                    self._callbacks.on_close()
                return
            self._schedule_reconnect(
                RECONNECT_DELAY_S * self._session_not_found_retries,
                f"4001 attempt {self._session_not_found_retries}/{MAX_SESSION_NOT_FOUND_RETRIES}",
            )
            return

        if (
            previous_state == "connected"
            and self._reconnect_attempts < MAX_RECONNECT_ATTEMPTS
        ):
            self._reconnect_attempts += 1
            self._schedule_reconnect(
                RECONNECT_DELAY_S,
                f"attempt {self._reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS}",
            )
        else:
            log.debug("[SessionsWebSocket] Not reconnecting")
            if self._callbacks.on_close:
                self._callbacks.on_close()

    def _schedule_reconnect(self, delay: float, label: str) -> None:
        if self._callbacks.on_reconnecting:
            self._callbacks.on_reconnecting()
        log.debug(
            "[SessionsWebSocket] Scheduling reconnect (%s) in %.1fs",
            label,
            delay,
        )
        loop = asyncio.get_event_loop()
        self._reconnect_timer = loop.call_later(
            delay, lambda: asyncio.ensure_future(self.connect())
        )

    def _cancel_reconnect_timer(self) -> None:
        if self._reconnect_timer is not None:
            self._reconnect_timer.cancel()
            self._reconnect_timer = None

    def _start_ping_task(self, ws: object) -> None:
        self._stop_ping_task()

        async def _ping_loop() -> None:
            while self._state == "connected":
                await asyncio.sleep(PING_INTERVAL_S)
                if self._state == "connected" and ws is self._ws:
                    try:
                        await ws.ping()  # type: ignore
                    except Exception:
                        pass

        self._ping_task = asyncio.ensure_future(_ping_loop())

    def _stop_ping_task(self) -> None:
        if self._ping_task is not None and not self._ping_task.done():
            self._ping_task.cancel()
        self._ping_task = None

    def _send_json(self, data: dict) -> None:
        if self._ws is None:
            return
        asyncio.ensure_future(self._async_send(json.dumps(data)))

    async def _async_send(self, data: str) -> None:
        if self._ws is not None:
            try:
                await self._ws.send(data)  # type: ignore
            except Exception as exc:
                log.error("[SessionsWebSocket] Send failed: %s", exc)
