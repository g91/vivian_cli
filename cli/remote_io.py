"""Remote I/O — mirrors src/cli/remoteIO.ts.

Bidirectional streaming for SDK mode with session tracking.
Supports SSE and WebSocket transports via ``transports/``.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse

from .structured_io import StructuredIO
from .transports.transport import Transport
from .transports.transport_utils import get_transport_for_url

logger = logging.getLogger(__name__)


class RemoteIO(StructuredIO):
    """StructuredIO that reads from a remote SSE/WebSocket stream.

    :param stream_url: The session URL (ws://, wss://, http://, https://).
    :param auth_token: Bearer token for the session ingress.
    """

    def __init__(
        self,
        stream_url: str,
        auth_token: Optional[str] = None,
        replay_user_messages: bool = False,
    ) -> None:
        super().__init__(replay_user_messages=replay_user_messages)
        self._url = stream_url
        self._auth_token = auth_token or os.environ.get("vivian_SESSION_TOKEN")
        self._transport: Optional[Transport] = None
        self._is_bridge = os.environ.get("vivian_CODE_ENVIRONMENT_KIND") == "bridge"
        self._pending_data: asyncio.Queue[Optional[bytes]] = asyncio.Queue()
        self._connect_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Transport helpers

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        er_ver = os.environ.get("vivian_CODE_ENVIRONMENT_RUNNER_VERSION")
        if er_ver:
            headers["x-environment-runner-version"] = er_ver
        return headers

    # ------------------------------------------------------------------
    # Connection

    async def connect(self) -> None:
        """Connect to the remote stream and start processing data."""
        headers = self._build_headers()
        parsed = urlparse(self._url)

        self._transport = get_transport_for_url(self._url, headers)
        self._transport.set_on_data(self._handle_data)
        self._transport.set_on_close(self._handle_close)
        self._connect_task = asyncio.create_task(self._transport.connect())
        logger.debug("RemoteIO: connecting to %s", self._url)

    def _handle_data(self, data: str) -> None:
        for line in data.splitlines():
            if line.strip():
                try:
                    import json
                    msg = json.loads(line)
                    asyncio.get_event_loop().call_soon_threadsafe(
                        self._queue.put_nowait, msg
                    )
                except Exception:
                    pass

    def _handle_close(self, code: Optional[int] = None) -> None:
        logger.debug("RemoteIO: transport closed (code=%s)", code)
        asyncio.get_event_loop().call_soon_threadsafe(self._queue.put_nowait, None)

    # ------------------------------------------------------------------
    # Writing (override: write to transport instead of stdout)

    def write(self, msg: Any) -> None:
        if self._transport:
            from .ndjson import ndjson_safe_stringify
            asyncio.ensure_future(
                self._transport.send(ndjson_safe_stringify(msg) + "\n")
            )
        else:
            super().write(msg)

    # ------------------------------------------------------------------
    # Lifecycle

    async def close(self) -> None:
        if self._transport:
            await self._transport.close()
        if self._connect_task and not self._connect_task.done():
            self._connect_task.cancel()
        self.stop()
