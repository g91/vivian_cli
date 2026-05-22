"""Port of src/bridge/jwtUtils.ts

JWT decode utilities and token refresh scheduler for bridge sessions.
"""
from __future__ import annotations

import asyncio
import base64
import json
import math
import time
from typing import Any, Callable, Dict, Optional


def _format_duration(ms: int) -> str:
    if ms < 60_000:
        return f"{round(ms / 1000)}s"
    m = ms // 60_000
    s = round((ms % 60_000) / 1000)
    return f"{m}m {s}s" if s > 0 else f"{m}m"


def decodeJwtPayload(token: str) -> Optional[Any]:
    """
    Decode a JWT's payload segment without verifying the signature.
    Strips the `sk-ant-si-` session-ingress prefix if present.
    Returns the parsed JSON payload, or None if malformed.
    """
    jwt = token[len("sk-ant-si-"):] if token.startswith("sk-ant-si-") else token
    parts = jwt.split(".")
    if len(parts) != 3 or not parts[1]:
        return None
    try:
        # Add padding
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        payload_bytes = base64.urlsafe_b64decode(padded)
        return json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        return None


def decodeJwtExpiry(token: str) -> Optional[int]:
    """Decode the `exp` (expiry) claim from a JWT. Returns Unix seconds or None."""
    payload = decodeJwtPayload(token)
    if payload is not None and isinstance(payload, dict):
        exp = payload.get("exp")
        if isinstance(exp, (int, float)):
            return int(exp)
    return None


TOKEN_REFRESH_BUFFER_MS = 5 * 60 * 1000      # 5 minutes
FALLBACK_REFRESH_INTERVAL_MS = 30 * 60 * 1000  # 30 minutes
MAX_REFRESH_FAILURES = 3
REFRESH_RETRY_DELAY_MS = 60_000


def createTokenRefreshScheduler(
    get_access_token: Callable,
    on_refresh: Callable[[str, str], None],
    label: str,
    refresh_buffer_ms: int = TOKEN_REFRESH_BUFFER_MS,
) -> Dict[str, Any]:
    """
    Creates a token refresh scheduler that proactively refreshes session tokens
    before they expire.
    """
    _timers: Dict[str, asyncio.TimerHandle] = {}
    _failure_counts: Dict[str, int] = {}
    _generations: Dict[str, int] = {}

    def _next_generation(session_id: str) -> int:
        gen = _generations.get(session_id, 0) + 1
        _generations[session_id] = gen
        return gen

    def schedule(session_id: str, token: str) -> None:
        expiry = decodeJwtExpiry(token)
        if expiry is None:
            try:
                from ..utils.debug import log_for_debugging
                log_for_debugging(f"[{label}:token] Could not decode JWT expiry for sessionId={session_id}")
            except Exception:
                pass
            return

        existing = _timers.get(session_id)
        if existing:
            existing.cancel()

        gen = _next_generation(session_id)
        delay_ms = expiry * 1000 - int(time.time() * 1000) - refresh_buffer_ms

        if delay_ms <= 0:
            asyncio.ensure_future(_do_refresh(session_id, gen))
            return

        loop = asyncio.get_event_loop()
        handle = loop.call_later(delay_ms / 1000.0, lambda: asyncio.ensure_future(_do_refresh(session_id, gen)))
        _timers[session_id] = handle

    def schedule_from_expires_in(session_id: str, expires_in_seconds: int) -> None:
        existing = _timers.get(session_id)
        if existing:
            existing.cancel()
        gen = _next_generation(session_id)
        delay_ms = max(expires_in_seconds * 1000 - refresh_buffer_ms, 30_000)
        loop = asyncio.get_event_loop()
        handle = loop.call_later(delay_ms / 1000.0, lambda: asyncio.ensure_future(_do_refresh(session_id, gen)))
        _timers[session_id] = handle

    async def _do_refresh(session_id: str, gen: int) -> None:
        oauth_token: Optional[str] = None
        try:
            result = get_access_token()
            if asyncio.iscoroutine(result):
                oauth_token = await result
            else:
                oauth_token = result
        except Exception as err:
            try:
                from ..utils.debug import log_for_debugging
                log_for_debugging(f"[{label}:token] getAccessToken threw: {err}", level="error")
            except Exception:
                pass

        if _generations.get(session_id) != gen:
            return

        if not oauth_token:
            failures = _failure_counts.get(session_id, 0) + 1
            _failure_counts[session_id] = failures
            if failures < MAX_REFRESH_FAILURES:
                loop = asyncio.get_event_loop()
                handle = loop.call_later(REFRESH_RETRY_DELAY_MS / 1000.0, lambda: asyncio.ensure_future(_do_refresh(session_id, gen)))
                _timers[session_id] = handle
            return

        _failure_counts.pop(session_id, None)
        on_refresh(session_id, oauth_token)

        # Schedule follow-up refresh
        loop = asyncio.get_event_loop()
        handle = loop.call_later(FALLBACK_REFRESH_INTERVAL_MS / 1000.0, lambda: asyncio.ensure_future(_do_refresh(session_id, gen)))
        _timers[session_id] = handle

    def cancel(session_id: str) -> None:
        _next_generation(session_id)
        existing = _timers.pop(session_id, None)
        if existing:
            existing.cancel()
        _failure_counts.pop(session_id, None)

    def cancel_all() -> None:
        for session_id in list(_generations.keys()):
            _next_generation(session_id)
        for handle in _timers.values():
            handle.cancel()
        _timers.clear()
        _failure_counts.clear()

    return {
        "schedule": schedule,
        "scheduleFromExpiresIn": schedule_from_expires_in,
        "cancel": cancel,
        "cancelAll": cancel_all,
    }
