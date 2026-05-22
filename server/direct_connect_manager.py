"""Direct-connect session manager — mirrors src/server/directConnectManager.ts."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Callable, Optional
from uuid import uuid4

log = logging.getLogger(__name__)

IGNORED_MSG_TYPES = frozenset(
    (
        "control_response",
        "keep_alive",
        "control_cancel_request",
        "streamlined_text",
        "streamlined_tool_use_summary",
    )
)


@dataclass
class DirectConnectConfig:
    server_url: str
    session_id: str
    ws_url: str
    auth_token: Optional[str] = None


@dataclass
class DirectConnectCallbacks:
    on_message: Callable[[dict], None]
    on_permission_request: Callable[[dict, str], None]
    on_connected: Optional[Callable[[], None]] = None
    on_disconnected: Optional[Callable[[], None]] = None
    on_error: Optional[Callable[[Exception], None]] = None


class DirectConnectSessionManager:
    """WebSocket manager for a direct session (ndjson line protocol)."""

    def __init__(
        self,
        config: DirectConnectConfig,
        callbacks: DirectConnectCallbacks,
    ) -> None:
        self._config = config
        self._callbacks = callbacks
        self._ws = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Open the WebSocket connection (non-async, Bun/browser style)."""
        import threading
        import asyncio

        def _run() -> None:
            asyncio.run(self._async_connect())

        threading.Thread(target=_run, daemon=True).start()

    def send_message(self, content) -> bool:
        """Send a user message (mirrors sendMessage in TS)."""
        if not self.is_connected():
            return False
        msg = json.dumps(
            {
                "type": "user",
                "message": {"role": "user", "content": content},
                "parent_tool_use_id": None,
                "session_id": "",
            }
        )
        self._ws_send(msg)
        return True

    def respond_to_permission_request(
        self,
        request_id: str,
        result: dict,
    ) -> None:
        """Send a control_response for a permission request."""
        if not self.is_connected():
            return
        behavior = result.get("behavior", "deny")
        inner: dict = {"behavior": behavior}
        if behavior == "allow":
            inner["updatedInput"] = result.get("updated_input")
        else:
            inner["message"] = result.get("message")

        msg = json.dumps(
            {
                "type": "control_response",
                "response": {
                    "subtype": "success",
                    "request_id": request_id,
                    "response": inner,
                },
            }
        )
        self._ws_send(msg)

    def send_interrupt(self) -> None:
        """Cancel the current request."""
        if not self.is_connected():
            return
        msg = json.dumps(
            {
                "type": "control_request",
                "request_id": str(uuid4()),
                "request": {"subtype": "interrupt"},
            }
        )
        self._ws_send(msg)

    def disconnect(self) -> None:
        ws = self._ws
        self._ws = None
        if ws is not None:
            try:
                import asyncio
                asyncio.ensure_future(ws.close())
            except Exception:
                pass

    def is_connected(self) -> bool:
        return self._ws is not None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _async_connect(self) -> None:
        try:
            import websockets  # type: ignore

            headers: dict = {}
            if self._config.auth_token:
                headers["authorization"] = f"Bearer {self._config.auth_token}"

            async with websockets.connect(
                self._config.ws_url, additional_headers=headers
            ) as ws:
                self._ws = ws
                if self._callbacks.on_connected:
                    self._callbacks.on_connected()

                async for raw in ws:
                    data = raw if isinstance(raw, str) else raw.decode()
                    for line in data.split("\n"):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            parsed = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if not isinstance(parsed, dict) or "type" not in parsed:
                            continue
                        self._handle_message(parsed)

        except Exception as exc:
            log.debug("[DirectConnect] connection error: %s", exc)
            if self._callbacks.on_error:
                self._callbacks.on_error(exc if isinstance(exc, Exception) else Exception(str(exc)))
        finally:
            self._ws = None
            if self._callbacks.on_disconnected:
                self._callbacks.on_disconnected()

    def _handle_message(self, parsed: dict) -> None:
        msg_type = parsed.get("type", "")

        if msg_type == "control_request":
            subtype = (parsed.get("request") or {}).get("subtype")
            request_id = parsed.get("request_id", "")
            if subtype == "can_use_tool":
                self._callbacks.on_permission_request(parsed.get("request", {}), request_id)
            else:
                log.debug("[DirectConnect] Unsupported control request subtype: %s", subtype)
                self._send_error_response(
                    request_id, f"Unsupported control request subtype: {subtype}"
                )
            return

        # Drop internal protocol messages
        if msg_type in IGNORED_MSG_TYPES:
            return
        if msg_type == "system" and (parsed.get("subtype") == "post_turn_summary"):
            return

        self._callbacks.on_message(parsed)

    def _send_error_response(self, request_id: str, error: str) -> None:
        if not self.is_connected():
            return
        msg = json.dumps(
            {
                "type": "control_response",
                "response": {
                    "subtype": "error",
                    "request_id": request_id,
                    "error": error,
                },
            }
        )
        self._ws_send(msg)

    def _ws_send(self, data: str) -> None:
        if self._ws is not None:
            import asyncio
            asyncio.ensure_future(self._ws.send(data))
