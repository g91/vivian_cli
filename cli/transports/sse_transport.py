"""SSE Transport — mirrors src/cli/transports/SSETransport.ts.

Reads a server-sent events stream (GET) and writes via HTTP POST.
Reconnects automatically with exponential back-off.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Optional
from urllib.parse import urlparse

import httpx

from .transport import Transport

logger = logging.getLogger(__name__)

RECONNECT_BASE_DELAY_S = 1.0
RECONNECT_MAX_DELAY_S = 30.0
RECONNECT_GIVE_UP_S = 600.0
LIVENESS_TIMEOUT_S = 45.0

PERMANENT_HTTP_CODES = {401, 403, 404}

POST_MAX_RETRIES = 10
POST_BASE_DELAY_S = 0.5
POST_MAX_DELAY_S = 8.0

_DOUBLE_NL = re.compile(r"\r?\n\r?\n")


@dataclass
class SSEFrame:
    event: Optional[str] = None
    id: Optional[str] = None
    data: Optional[str] = None


def parse_sse_frames(buffer: str) -> tuple[list[SSEFrame], str]:
    """Parse complete SSE frames from *buffer*.  Returns (frames, remaining)."""
    frames: list[SSEFrame] = []
    pos = 0
    while True:
        m = _DOUBLE_NL.search(buffer, pos)
        if not m:
            break
        raw = buffer[pos : m.start()]
        pos = m.end()
        if not raw.strip():
            continue
        frame = SSEFrame()
        is_comment = False
        for line in raw.splitlines():
            if line.startswith(":"):
                is_comment = True
                continue
            if ":" in line:
                key, _, val = line.partition(":")
                val = val.lstrip(" ")
                if key == "event":
                    frame.event = val
                elif key == "id":
                    frame.id = val
                elif key == "data":
                    frame.data = (frame.data + "\n" + val) if frame.data else val
            elif line:
                frame.event = line  # bare field name
        if not is_comment or frame.data is not None:
            frames.append(frame)
    return frames, buffer[pos:]


class SSETransport(Transport):
    """HTTP SSE reads + HTTP POST writes transport.

    Args:
        url: The SSE endpoint URL (http:// or https://).
        headers: Static headers (e.g. Authorization).
        session_id: Optional session identifier sent as a query param.
        refresh_headers: Called before every reconnection to pick up fresh tokens.
    """

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        session_id: Optional[str] = None,
        refresh_headers: Callable[[], dict[str, str]] | None = None,
    ) -> None:
        self._url = url
        self._headers = dict(headers or {})
        self._session_id = session_id
        self._refresh_headers = refresh_headers
        self._closed = False
        self._last_event_id: Optional[str] = None
        self._post_url: Optional[str] = None  # set to base URL for POSTs

    async def connect(self) -> None:
        """Start the SSE read loop with automatic reconnection."""
        start = time.monotonic()
        delay = RECONNECT_BASE_DELAY_S
        while not self._closed:
            headers = dict(self._headers)
            if self._refresh_headers:
                headers.update(self._refresh_headers())
            if self._last_event_id:
                headers["Last-Event-ID"] = self._last_event_id
            try:
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream("GET", self._url, headers=headers) as resp:
                        if resp.status_code in PERMANENT_HTTP_CODES:
                            logger.error(
                                "SSETransport: permanent HTTP %s — closing",
                                resp.status_code,
                            )
                            self._closed = True
                            self._emit_close(resp.status_code)
                            return
                        buffer = ""
                        async for chunk in resp.aiter_text():
                            if self._closed:
                                return
                            buffer += chunk
                            frames, buffer = parse_sse_frames(buffer)
                            for frame in frames:
                                if frame.id:
                                    self._last_event_id = frame.id
                                if frame.data is not None:
                                    self._emit_data(frame.data)
                        # Stream ended cleanly
                        if self._closed:
                            return
            except Exception as exc:
                if self._closed:
                    return
                elapsed = time.monotonic() - start
                if elapsed > RECONNECT_GIVE_UP_S:
                    logger.error("SSETransport: giving up after %.0fs: %s", elapsed, exc)
                    self._emit_close(None)
                    return
                logger.debug("SSETransport: reconnect in %.1fs (err=%s)", delay, exc)
                await asyncio.sleep(delay)
                delay = min(delay * 2, RECONNECT_MAX_DELAY_S)

    async def send(self, data: str) -> None:
        """POST *data* to the session ingress endpoint."""
        if not self._post_url:
            # Derive POST URL from SSE URL (drop /worker/events/stream suffix)
            parsed = urlparse(self._url)
            path = re.sub(r"/worker/events/stream$", "", parsed.path)
            from urllib.parse import urlunparse
            self._post_url = urlunparse(parsed._replace(path=path))
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
                    if resp.status_code in PERMANENT_HTTP_CODES:
                        raise RuntimeError(f"POST rejected: {resp.status_code}")
            except Exception as exc:
                if attempt >= POST_MAX_RETRIES - 1:
                    raise
                delay = min(POST_BASE_DELAY_S * (2 ** attempt), POST_MAX_DELAY_S)
                await asyncio.sleep(delay)

    async def close(self) -> None:
        self._closed = True
