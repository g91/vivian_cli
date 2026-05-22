"""Port of src/bridge/debugUtils.ts

Bridge debug utilities: secret redaction, error message extraction,
debug truncation, logging helpers.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

DEBUG_MSG_LIMIT = 2000

_SECRET_FIELD_NAMES = [
    "session_ingress_token",
    "environment_secret",
    "access_token",
    "secret",
    "token",
]

_SECRET_PATTERN = re.compile(
    r'"(' + "|".join(_SECRET_FIELD_NAMES) + r'")\s*:\s*"([^"]*)"',
    re.IGNORECASE,
)

_REDACT_MIN_LENGTH = 16


def redactSecrets(s: str) -> str:
    """Redact sensitive field values in JSON strings."""
    def _replacer(match: re.Match) -> str:
        field = match.group(1)
        value = match.group(2)
        if len(value) < _REDACT_MIN_LENGTH:
            return f'"{field}":"[REDACTED]"'
        redacted = f"{value[:8]}...{value[-4:]}"
        return f'"{field}":"{redacted}"'

    return _SECRET_PATTERN.sub(_replacer, s)


def debugTruncate(s: str) -> str:
    """Truncate a string for debug logging, collapsing newlines."""
    flat = s.replace("\n", "\\n")
    if len(flat) <= DEBUG_MSG_LIMIT:
        return flat
    return flat[:DEBUG_MSG_LIMIT] + f"... ({len(flat)} chars)"


def debugBody(data: Any) -> str:
    """Truncate a JSON-serializable value for debug logging."""
    raw = data if isinstance(data, str) else json.dumps(data)
    s = redactSecrets(raw)
    if len(s) <= DEBUG_MSG_LIMIT:
        return s
    return s[:DEBUG_MSG_LIMIT] + f"... ({len(s)} chars)"


def describeAxiosError(err: Any) -> str:
    """Extract a descriptive error message from an httpx/requests error."""
    msg = str(err)
    # Check for httpx.HTTPStatusError or similar response objects
    response = getattr(err, "response", None)
    if response is not None:
        try:
            data = response.json()
            if isinstance(data, dict):
                detail = data.get("message")
                if not detail:
                    error_obj = data.get("error")
                    if isinstance(error_obj, dict):
                        detail = error_obj.get("message")
                if isinstance(detail, str):
                    return f"{msg}: {detail}"
        except Exception:
            pass
    return msg


def extractHttpStatus(err: Any) -> Optional[int]:
    """Extract the HTTP status code from an httpx/requests error."""
    response = getattr(err, "response", None)
    if response is not None:
        status = getattr(response, "status_code", None)
        if isinstance(status, int):
            return status
    return None


def extractErrorDetail(data: Any) -> Optional[str]:
    """Pull a human-readable message from an API error response body."""
    if not isinstance(data, dict):
        return None
    if isinstance(data.get("message"), str):
        return data["message"]
    error_obj = data.get("error")
    if isinstance(error_obj, dict) and isinstance(error_obj.get("message"), str):
        return error_obj["message"]
    return None


def logBridgeSkip(reason: str, debug_msg: Optional[str] = None, v2: Optional[bool] = None) -> None:
    """Log a bridge init skip."""
    if debug_msg:
        try:
            from ..utils.debug import log_for_debugging
            log_for_debugging(debug_msg)
        except Exception:
            pass
    try:
        from ..services.analytics import log_event
        payload: dict = {"reason": reason}
        if v2 is not None:
            payload["v2"] = v2
        log_event("tengu_bridge_repl_skipped", payload)
    except Exception:
        pass
