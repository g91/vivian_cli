"""Transport selection helper — mirrors src/cli/transports/transportUtils.ts.

Priority order:
  1. SSETransport when ``vivian_CODE_USE_CCR_V2`` env var is set.
  2. HybridTransport when ``vivian_CODE_POST_FOR_SESSION_INGRESS_V2`` is set.
  3. WebSocketTransport for ws:// / wss:// URLs (default).
"""
from __future__ import annotations

import os
from typing import Callable, Optional
from urllib.parse import urlparse, urlunparse

from .hybrid_transport import HybridTransport
from .sse_transport import SSETransport
from .transport import Transport
from .websocket_transport import WebSocketTransport


def _is_env_truthy(val: Optional[str]) -> bool:
    return val is not None and val.lower() not in ("0", "false", "no", "")


def get_transport_for_url(
    url: str,
    headers: dict[str, str] | None = None,
    session_id: Optional[str] = None,
    refresh_headers: Callable[[], dict[str, str]] | None = None,
) -> Transport:
    """Return the appropriate transport for *url*.

    Args:
        url: Session URL (ws://, wss://, http://, https://).
        headers: Static headers to send on every request.
        session_id: Optional session identifier.
        refresh_headers: Called before reconnections to refresh auth tokens.

    Returns:
        A :class:`Transport` instance (not yet connected).
    """
    h = dict(headers or {})

    if _is_env_truthy(os.environ.get("vivian_CODE_USE_CCR_V2")):
        # v2: SSE reads, POST writes — derive /worker/events/stream suffix
        parsed = urlparse(url)
        scheme = "https" if parsed.scheme in ("wss", "https") else "http"
        path = parsed.path.rstrip("/") + "/worker/events/stream"
        sse_url = urlunparse(parsed._replace(scheme=scheme, path=path))
        return SSETransport(sse_url, h, session_id, refresh_headers)

    parsed = urlparse(url)
    if parsed.scheme in ("ws", "wss"):
        if _is_env_truthy(os.environ.get("vivian_CODE_POST_FOR_SESSION_INGRESS_V2")):
            return HybridTransport(url, h, session_id, refresh_headers)
        return WebSocketTransport(url, h, session_id, refresh_headers)

    if parsed.scheme in ("http", "https"):
        # Treat plain HTTP URLs as SSE endpoints
        return SSETransport(url, h, session_id, refresh_headers)

    raise ValueError(f"Unsupported URL scheme: {parsed.scheme!r} in {url!r}")
