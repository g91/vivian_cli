"""Port of src/bridge/workSecret.ts

Work secret decode utilities and CCR v2 helpers.
"""
from __future__ import annotations

import base64
import json
from typing import Any, Dict

import httpx


def decodeWorkSecret(secret: str) -> Dict[str, Any]:
    """Decode a base64url-encoded work secret and validate its version."""
    try:
        padded = secret + "=" * (-len(secret) % 4)
        raw = base64.urlsafe_b64decode(padded).decode("utf-8")
        parsed = json.loads(raw)
    except Exception as e:
        raise ValueError(f"Invalid work secret encoding: {e}") from e

    if not isinstance(parsed, dict) or parsed.get("version") != 1:
        version = parsed.get("version") if isinstance(parsed, dict) else "unknown"
        raise ValueError(f"Unsupported work secret version: {version}")

    sit = parsed.get("session_ingress_token")
    if not isinstance(sit, str) or not sit:
        raise ValueError("Invalid work secret: missing or empty session_ingress_token")

    if not isinstance(parsed.get("api_base_url"), str):
        raise ValueError("Invalid work secret: missing api_base_url")

    return parsed


def buildSdkUrl(api_base_url: str, session_id: str) -> str:
    """
    Build a WebSocket SDK URL from the API base URL and session ID.
    Uses /v2/ for localhost and /v1/ for production.
    """
    is_localhost = "localhost" in api_base_url or "127.0.0.1" in api_base_url
    protocol = "ws" if is_localhost else "wss"
    version = "v2" if is_localhost else "v1"
    import re
    host = re.sub(r"^https?://", "", api_base_url).rstrip("/")
    return f"{protocol}://{host}/{version}/session_ingress/ws/{session_id}"


def sameSessionId(a: str, b: str) -> bool:
    """
    Compare two session IDs regardless of their tagged-ID prefix.
    Supports cse_* and session_* tag formats that share the same UUID body.
    """
    if a == b:
        return True
    a_body = a[a.rfind("_") + 1:]
    b_body = b[b.rfind("_") + 1:]
    return len(a_body) >= 4 and a_body == b_body


def buildCCRv2SdkUrl(api_base_url: str, session_id: str) -> str:
    """Build a CCR v2 session URL (HTTP, not ws://)."""
    base = api_base_url.rstrip("/")
    return f"{base}/v1/code/sessions/{session_id}"


async def registerWorker(session_url: str, access_token: str) -> int:
    """
    Register this bridge as the worker for a CCR v2 session.
    Returns the worker_epoch.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{session_url}/worker/register",
            json={},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            },
        )
        response.raise_for_status()
        data = response.json()

    raw = data.get("worker_epoch")
    epoch = int(raw) if isinstance(raw, str) else raw
    if not isinstance(epoch, int) or not (-(2**53) <= epoch <= 2**53):
        raise ValueError(f"registerWorker: invalid worker_epoch in response: {data}")
    return epoch
