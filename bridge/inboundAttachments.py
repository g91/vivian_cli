"""Port of src/bridge/inboundAttachments.ts

Resolve file_uuid attachments on inbound bridge user messages.
Fetches via GET /api/oauth/files/{uuid}/content, writes to ~/.vivian/uploads/,
and returns @path refs to prepend.
"""
from __future__ import annotations

import os
import uuid as _uuid
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

DOWNLOAD_TIMEOUT_MS = 30_000


def _debug(msg: str) -> None:
    try:
        from ..utils.debug import log_for_debugging
        log_for_debugging(f"[bridge:inbound-attach] {msg}")
    except Exception:
        pass


def extractInboundAttachments(msg: Any) -> List[Dict[str, str]]:
    """Pull file_attachments off a loosely-typed inbound message."""
    if not isinstance(msg, dict) or "file_attachments" in msg is False:
        return []
    attachments = msg.get("file_attachments", [])
    if not isinstance(attachments, list):
        return []
    result = []
    for att in attachments:
        if isinstance(att, dict) and isinstance(att.get("file_uuid"), str) and isinstance(att.get("file_name"), str):
            result.append({"file_uuid": att["file_uuid"], "file_name": att["file_name"]})
    return result


def _sanitize_file_name(name: str) -> str:
    """Strip path components and keep only filename-safe chars."""
    base = os.path.basename(name)
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", base)
    return safe or "attachment"


def _uploads_dir() -> str:
    try:
        from ..utils.env_utils import get_vivian_config_home_dir
        from ..bootstrap.state import getSessionId
        home = get_vivian_config_home_dir()
        session_id = getSessionId()
    except Exception:
        home = os.path.expanduser("~/.vivian")
        session_id = "unknown"
    return os.path.join(home, "uploads", session_id)


async def _resolve_one(att: Dict[str, str]) -> Optional[str]:
    """Fetch + write one attachment. Returns absolute path or None on failure."""
    try:
        from .bridgeConfig import getBridgeAccessToken, getBridgeBaseUrl
        token = getBridgeAccessToken()
    except Exception:
        _debug("skip: no oauth token")
        return None

    if not token:
        _debug("skip: no oauth token")
        return None

    try:
        import httpx
        from .bridgeConfig import getBridgeBaseUrl
        base_url = getBridgeBaseUrl()
        url = f"{base_url}/api/oauth/files/{att['file_uuid']}/content"
        async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT_MS / 1000.0) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code != 200:
            _debug(f"fetch {att['file_uuid']} failed: status={resp.status_code}")
            return None
        data = resp.content
    except Exception as e:
        _debug(f"fetch {att['file_uuid']} threw: {e}")
        return None

    safe_name = _sanitize_file_name(att["file_name"])
    prefix = re.sub(r"[^a-zA-Z0-9_-]", "_", att["file_uuid"][:8] or str(_uuid.uuid4())[:8])
    directory = _uploads_dir()
    out_path = os.path.join(directory, f"{prefix}-{safe_name}")

    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        Path(out_path).write_bytes(data)
    except Exception as e:
        _debug(f"write {out_path} failed: {e}")
        return None

    _debug(f"resolved {att['file_uuid']} → {out_path} ({len(data)} bytes)")
    return out_path


async def resolveInboundAttachments(attachments: List[Dict[str, str]]) -> str:
    """
    Resolve all attachments to a prefix string of @path refs.
    Returns empty string if none resolved.
    """
    if not attachments:
        return ""
    _debug(f"resolving {len(attachments)} attachment(s)")
    import asyncio
    paths = await asyncio.gather(*[_resolve_one(att) for att in attachments])
    ok = [p for p in paths if p is not None]
    if not ok:
        return ""
    return " ".join(f'@"{p}"' for p in ok) + " "


def prependPathRefs(
    content: Union[str, List[Dict[str, Any]]],
    prefix: str,
) -> Union[str, List[Dict[str, Any]]]:
    """Prepend @path refs to content (string or block array)."""
    if not prefix:
        return content
    if isinstance(content, str):
        return prefix + content
    # Find last text block
    last_text_idx = -1
    for i in range(len(content) - 1, -1, -1):
        if content[i].get("type") == "text":
            last_text_idx = i
            break
    if last_text_idx >= 0:
        b = content[last_text_idx]
        updated = {**b, "text": prefix + b.get("text", "")}
        return [*content[:last_text_idx], updated, *content[last_text_idx + 1:]]
    # No text block — append one at the end
    return [*content, {"type": "text", "text": prefix.rstrip()}]


async def resolveAndPrepend(
    msg: Any,
    content: Union[str, List[Dict[str, Any]]],
) -> Union[str, List[Dict[str, Any]]]:
    """Convenience: extract + resolve + prepend. No-op when no file_attachments."""
    attachments = extractInboundAttachments(msg)
    if not attachments:
        return content
    prefix = await resolveInboundAttachments(attachments)
    return prependPathRefs(content, prefix)
