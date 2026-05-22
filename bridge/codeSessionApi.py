"""Port of src/bridge/codeSessionApi.ts

Thin HTTP wrappers for the CCR v2 code-session API.
Callers supply explicit accessToken + baseUrl.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

import httpx

ANTHROPIC_VERSION = "2023-06-01"


def _oauth_headers(access_token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "anthropic-version": ANTHROPIC_VERSION,
    }


def _debug(msg: str) -> None:
    try:
        from ..utils.debug import log_for_debugging
        log_for_debugging(msg)
    except Exception:
        pass


async def createCodeSession(
    base_url: str,
    access_token: str,
    title: str,
    timeout_ms: int,
    tags: Optional[List[str]] = None,
) -> Optional[str]:
    """Create a CCR v2 code session. Returns session ID (cse_*) or None on failure."""
    url = f"{base_url}/v1/code/sessions"
    payload: Dict[str, Any] = {"title": title, "bridge": {}}
    if tags:
        payload["tags"] = tags

    try:
        async with httpx.AsyncClient(timeout=timeout_ms / 1000.0) as client:
            resp = await client.post(
                url,
                json=payload,
                headers=_oauth_headers(access_token),
            )
    except Exception as err:
        _debug(f"[code-session] Session create request failed: {err}")
        return None

    if resp.status_code not in (200, 201):
        try:
            from .debugUtils import extractErrorDetail
            detail = extractErrorDetail(resp.json())
        except Exception:
            detail = None
        _debug(f"[code-session] Session create failed {resp.status_code}" + (f": {detail}" if detail else ""))
        return None

    try:
        data = resp.json()
        session_id = data["session"]["id"]
        if not isinstance(session_id, str) or not session_id.startswith("cse_"):
            raise ValueError("bad session id")
        return session_id
    except Exception:
        _debug(f"[code-session] No session.id (cse_*) in response: {str(resp.text)[:200]}")
        return None


class RemoteCredentials(TypedDict):
    worker_jwt: str
    api_base_url: str
    expires_in: int
    worker_epoch: int


async def fetchRemoteCredentials(
    session_id: str,
    base_url: str,
    access_token: str,
    timeout_ms: int,
    trusted_device_token: Optional[str] = None,
) -> Optional[RemoteCredentials]:
    """Fetch bridge credentials from POST /v1/code/sessions/{id}/bridge."""
    url = f"{base_url}/v1/code/sessions/{session_id}/bridge"
    headers = _oauth_headers(access_token)
    if trusted_device_token:
        headers["X-Trusted-Device-Token"] = trusted_device_token

    try:
        async with httpx.AsyncClient(timeout=timeout_ms / 1000.0) as client:
            resp = await client.post(url, json={}, headers=headers)
    except Exception as err:
        _debug(f"[code-session] /bridge request failed: {err}")
        return None

    if resp.status_code != 200:
        try:
            from .debugUtils import extractErrorDetail
            detail = extractErrorDetail(resp.json())
        except Exception:
            detail = None
        _debug(f"[code-session] /bridge failed {resp.status_code}" + (f": {detail}" if detail else ""))
        return None

    try:
        data = resp.json()
        raw_epoch = data["worker_epoch"]
        epoch = int(raw_epoch) if isinstance(raw_epoch, str) else raw_epoch
        if not isinstance(epoch, int) or not (-(2**53) <= epoch <= 2**53):
            raise ValueError(f"invalid worker_epoch: {raw_epoch}")
        return RemoteCredentials(
            worker_jwt=data["worker_jwt"],
            api_base_url=data["api_base_url"],
            expires_in=int(data["expires_in"]),
            worker_epoch=epoch,
        )
    except Exception as e:
        _debug(f"[code-session] /bridge response malformed: {e}: {str(resp.text)[:200]}")
        return None
