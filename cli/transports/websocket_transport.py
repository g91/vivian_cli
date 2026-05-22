"""WebSocket Transport — mirrors src/cli/transports/WebSocketTransport.ts.

Full-duplex WebSocket connection with automatic reconnection and
keep-alive pings.  Requires the ``websockets`` package.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Callable, Optional

from .transport import Transport

logger = logging.getLogger(__name__)

KEEP_ALIVE_FRAME = '{"type":"keep_alive"}\n'

DEFAULT_MAX_BUFFER_SIZE = 1000
DEFAULT_BASE_RECONNECT_DELAY_S = 1.0
DEFAULT_MAX_RECONNECT_DELAY_S = 30.0
DEFAULT_RECONNECT_GIVE_UP_S = 600.0
DEFAULT_PING_INTERVAL_S = 10.0
DEFAULT_KEEPALIVE_INTERVAL_S = 300.0

SLEEP_DETECTION_THRESHOLD_S = DEFAULT_MAX_RECONNECT_DELAY_S * 2

PERMANENT_CLOSE_CODES = {1002, 4001, 4003}


class WebSocketTransport(Transport):
    """WebSocket reads + WebSocket writes transport.

    Args:
        url: The WebSocket endpoint URL (ws:// or wss://).
        headers: Static request headers (e.g. Authorization).
        session_id: Optional session identifier.
        refresh_headers: Called before every reconnection for fresh tokens.
        auto_reconnect: Disable to let the caller handle recovery.
        is_bridge: When True, enables bridge-specific telemetry.
    """

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        session_id: Optional[str] = None,
        refresh_headers: Callable[[], dict[str, str]] | None = None,
        auto_reconnect: bool = True,
        is_bridge: bool = False,
    ) -> None:
        self._url = url
        self._headers = dict(headers or {})
        self._session_id = session_id
        self._refresh_headers = refresh_headers
        self._auto_reconnect = auto_reconnect
        self._is_bridge = is_bridge
        self._ws = None
        self._state: str = "idle"
        self._send_queue: deque[str] = deque(maxlen=DEFAULT_MAX_BUFFER_SIZE)
        self._reconnect_delay_s = DEFAULT_BASE_RECONNECT_DELAY_S
        self._closed = False

    async def connect(self) -> None:
        """Connect and maintain the WebSocket session."""
        try:
            import websockets
        except ImportError:
            raise RuntimeError(
                "websockets package required for WebSocketTransport. "
                "Install with: pip install websockets"
            )
        start = time.monotonic()
        last_attempt = start

        while not self._closed:
            now = time.monotonic()
            # Sleep detection: if the gap is very large, reset the budget
            if now - last_attempt > SLEEP_DETECTION_THRESHOLD_S:
                start = now
            last_attempt = now

            headers = dict(self._headers)
            if self._refresh_headers:
                headers.update(self._refresh_headers())
            try:
                self._state = "connected"
                async with websockets.connect(
                    self._url,
                    additional_headers=headers,
                    ping_interval=DEFAULT_PING_INTERVAL_S,
                ) as ws:
                    self._ws = ws
                    self._reconnect_delay_s = DEFAULT_BASE_RECONNECT_DELAY_S
                    # Flush buffered sends
                    while self._send_queue:
                        await ws.send(self._send_queue.popleft())
                    async for message in ws:
                        if self._closed:
                            return
                        self._emit_data(str(message))
            except Exception as exc:
                self._ws = None
                if self._closed:
                    return
                if hasattr(exc, "code") and exc.code in PERMANENT_CLOSE_CODES:  # type: ignore[union-attr]
                    logger.error(
                        "WebSocketTransport: permanent close %s — giving up", exc
                    )
                    self._closed = True
                    self._emit_close(getattr(exc, "code", None))
                    return
                elapsed = time.monotonic() - start
                if elapsed > DEFAULT_RECONNECT_GIVE_UP_S:
                    logger.error("WebSocketTransport: giving up after %.0fs", elapsed)
                    self._emit_close(None)
                    return
                if not self._auto_reconnect:
                    self._emit_close(None)
                    return
                self._state = "reconnecting"
                logger.debug(
                    "WebSocketTransport: reconnect in %.1fs (err=%s)",
                    self._reconnect_delay_s,
                    exc,
                )
                await asyncio.sleep(self._reconnect_delay_s)
                self._reconnect_delay_s = min(
                    self._reconnect_delay_s * 2, DEFAULT_MAX_RECONNECT_DELAY_S
                )

    async def send(self, data: str) -> None:
        if self._ws is not None:
            await self._ws.send(data)
        else:
            self._send_queue.append(data)

    async def close(self) -> None:
        self._closed = True
        self._state = "closed"
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
