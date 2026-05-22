"""Port of src/bridge/bridgeStatusUtil.ts

Bridge status state machine utilities, URL builders, shimmer animation helpers.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, Literal, Optional, TypedDict


# Status states
StatusState = Literal["idle", "attached", "titled", "reconnecting", "failed"]

TOOL_DISPLAY_EXPIRY_MS = 30_000
SHIMMER_INTERVAL_MS = 150


def timestamp() -> str:
    now = datetime.now()
    return f"{now.hour:02d}:{now.minute:02d}:{now.second:02d}"


def formatDuration(duration_ms: int) -> str:
    """Format a duration in milliseconds for bridge status output."""
    if duration_ms < 1000:
        return f"{duration_ms}ms"
    total_seconds = duration_ms // 1000
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def truncatePrompt(text: str, max_width: int) -> str:
    """Compatibility alias matching the TypeScript export name."""
    return _truncate_to_width(text, max_width)


def abbreviateActivity(summary: str) -> str:
    """Abbreviate a tool activity summary for the trail display."""
    return _truncate_to_width(summary, 30)


def buildBridgeConnectUrl(environment_id: str, ingress_url: Optional[str] = None) -> str:
    """Build the connect URL shown when the bridge is idle."""
    try:
        from ..constants.product import get_vivian_ai_base_url
        base_url = get_vivian_ai_base_url(None, ingress_url)
    except Exception:
        base_url = "https://api-vivian.d0a.net"
    return f"{base_url}/code?bridge={environment_id}"


def buildBridgeSessionUrl(
    session_id: str,
    environment_id: str,
    ingress_url: Optional[str] = None,
) -> str:
    """Build the session URL shown when a session is attached."""
    try:
        from ..constants.product import get_remote_session_url
        session_url = get_remote_session_url(session_id, ingress_url)
    except Exception:
        session_url = f"https://api-vivian.d0a.net/sessions/{session_id}"
    return f"{session_url}?bridge={environment_id}"


def computeGlimmerIndex(tick: int, message_width: int) -> int:
    """Compute the glimmer index for a reverse-sweep shimmer animation."""
    cycle_length = message_width + 20
    return message_width + 10 - (tick % cycle_length)


def computeShimmerSegments(
    text: str,
    glimmer_index: int,
) -> Dict[str, str]:
    """Split text into three segments by column position for shimmer rendering."""
    message_width = len(text)  # simplified — no grapheme segmentation
    shimmer_start = glimmer_index - 1
    shimmer_end = glimmer_index + 1

    if shimmer_start >= message_width or shimmer_end < 0:
        return {"before": text, "shimmer": "", "after": ""}

    clamped_start = max(0, shimmer_start)
    before = text[:clamped_start]
    shimmer = text[clamped_start : shimmer_end + 1]
    after = text[shimmer_end + 1 :]
    return {"before": before, "shimmer": shimmer, "after": after}


class BridgeStatusInfo(TypedDict):
    label: str
    color: str


def getBridgeStatus(
    error: Optional[str],
    connected: bool,
    session_active: bool,
    reconnecting: bool,
) -> BridgeStatusInfo:
    """Derive a status label and color from bridge connection state."""
    if error:
        return {"label": "Remote Control failed", "color": "error"}
    if reconnecting:
        return {"label": "Remote Control reconnecting", "color": "warning"}
    if session_active or connected:
        return {"label": "Remote Control active", "color": "success"}
    return {"label": "Remote Control connecting\u2026", "color": "warning"}


def buildIdleFooterText(url: str) -> str:
    return f"Code everywhere with the vivian app or {url}"


def buildActiveFooterText(url: str) -> str:
    return f"Continue coding in the vivian app or {url}"


FAILED_FOOTER_TEXT = "Something went wrong, please try again"


def wrapWithOsc8Link(text: str, url: str) -> str:
    """Wrap text in an OSC 8 terminal hyperlink."""
    return f"\x1b]8;;{url}\x07{text}\x1b]8;;\x07"


def _truncate_to_width(text: str, max_width: int) -> str:
    if len(text) <= max_width:
        return text
    return text[:max_width - 1] + "\u2026"
