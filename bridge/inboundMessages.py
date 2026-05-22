"""Port of src/bridge/inboundMessages.ts

Process inbound user messages from the bridge, extracting content and UUID.
"""
from __future__ import annotations

import base64
import re
from typing import Any, Dict, List, Optional, Tuple, Union


def extractInboundMessageFields(
    msg: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Process an inbound user message from the bridge, extracting content
    and UUID for enqueueing.

    Returns dict with 'content' and 'uuid', or None if message should be skipped.
    """
    if msg.get("type") != "user":
        return None
    content = (msg.get("message") or {}).get("content")
    if not content:
        return None
    if isinstance(content, list) and len(content) == 0:
        return None

    uuid_val: Optional[str] = None
    if "uuid" in msg and isinstance(msg["uuid"], str):
        uuid_val = msg["uuid"]

    return {
        "content": normalizeImageBlocks(content) if isinstance(content, list) else content,
        "uuid": uuid_val,
    }


def normalizeImageBlocks(
    blocks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Normalize image content blocks from bridge clients.
    iOS/web clients may send `mediaType` (camelCase) instead of `media_type`.
    """
    if not any(_is_malformed_base64_image(b) for b in blocks):
        return blocks

    return [_normalize_block(b) for b in blocks]


def _normalize_block(block: Dict[str, Any]) -> Dict[str, Any]:
    if not _is_malformed_base64_image(block):
        return block
    src = block.get("source", {})
    media_type = src.get("mediaType") if isinstance(src.get("mediaType"), str) and src["mediaType"] else None
    if not media_type:
        media_type = _detect_image_format_from_base64(src.get("data", ""))
    return {
        **block,
        "source": {
            "type": "base64",
            "media_type": media_type or "image/jpeg",
            "data": src.get("data", ""),
        },
    }


def _is_malformed_base64_image(block: Dict[str, Any]) -> bool:
    if block.get("type") != "image":
        return False
    source = block.get("source", {})
    if source.get("type") != "base64":
        return False
    return not source.get("media_type")


def _detect_image_format_from_base64(data: str) -> str:
    """Detect image MIME type from base64-encoded data by reading magic bytes."""
    try:
        raw = base64.b64decode(data[:16])
        if raw[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if raw[:3] == b"\xff\xd8\xff":
            return "image/jpeg"
        if raw[:6] in (b"GIF87a", b"GIF89a"):
            return "image/gif"
        if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
            return "image/webp"
    except Exception:
        pass
    return "image/jpeg"
