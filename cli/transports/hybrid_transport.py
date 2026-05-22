"""Hybrid Transport — mirrors src/cli/transports/HybridTransport.ts.

WebSocket reads + HTTP POST writes.  Falls back to POST when the WebSocket
is reconnecting so no messages are lost.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Callable, Optional

import httpx

from .websocket_transport import WebSocketTransport

logger = logging.getLogger(__name__)

POST_MAX_RETRIES = 10
POST_BASE_DELAY_S = 0.5
POST_MAX_DELAY_S = 8.0


class HybridTransport(WebSocketTransport):
    """WebSocket for reading; HTTP POST for writing.

    Derives the POST endpoint from the WebSocket URL by converting the
    protocol and appending ``/messages``.
    """

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        session_id: Optional[str] = None,
        refresh_headers: Callable[[], dict[str, str]] | None = None,
    ) -> None:
        super().__init__(url, headers, session_id, refresh_headers)
        # Build the HTTP POST URL from the WS URL
        post_url = url
        if post_url.startswith("wss://"):
            post_url = "https://" + post_url[6:]
        elif post_url.startswith("ws://"):
            post_url = "http://" + post_url[5:]
        self._post_url = post_url.rstrip("/") + "/messages"

    async def send(self, data: str) -> None:
        """POST *data* to the HTTP ingress endpoint."""
        headers = dict(self._headers)
        if self._refresh_headers:
            headers.update(self._refresh_headers())
        for attempt in range(POST_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        self._post_url,
                        content=data.encode(),
                        headers={**headers, "Content-Type": "application/json"},
                    )
                    if resp.status_code < 300:
                        return
                    if resp.status_code in {401, 403, 404}:
                        raise RuntimeError(f"POST rejected: {resp.status_code}")
            except Exception as exc:
                if attempt >= POST_MAX_RETRIES - 1:
                    raise
                delay = min(POST_BASE_DELAY_S * (2 ** attempt), POST_MAX_DELAY_S)
                logger.debug(
                    "HybridTransport: POST retry %d in %.1fs (%s)",
                    attempt + 1,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
