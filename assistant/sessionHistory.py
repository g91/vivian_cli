"""Port of src/assistant/sessionHistory.ts

Session history pagination via the CCR v1 events API.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

HISTORY_PAGE_SIZE = 100

# Type aliases matching TS shapes
HistoryPage = Dict[str, Any]
HistoryAuthCtx = Dict[str, Any]


async def createHistoryAuthCtx(session_id: str) -> HistoryAuthCtx:
    """Prepare auth + headers + base URL once, reuse across pages."""
    from ..utils.auth import get_vivian_ai_oauth_tokens
    from ..constants.oauth import get_oauth_config
    from ..utils.teleport.api import prepare_api_request, get_oauth_headers

    access_token, org_uuid = await prepare_api_request()
    oauth_config = get_oauth_config()
    base_url = f"{oauth_config['BASE_API_URL']}/v1/sessions/{session_id}/events"
    headers = {
        **get_oauth_headers(access_token),
        "anthropic-beta": "ccr-byoc-2025-07-29",
        "x-organization-uuid": org_uuid,
    }
    return {"baseUrl": base_url, "headers": headers}


async def _fetch_page(
    ctx: HistoryAuthCtx,
    params: Dict[str, Any],
    label: str,
) -> Optional[HistoryPage]:
    """Internal helper to fetch a single page of events."""
    try:
        import aiohttp
    except ImportError:
        raise ImportError("aiohttp required: pip install aiohttp")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                ctx["baseUrl"],
                headers=ctx["headers"],
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    try:
                        from ..utils.debug import log_for_debugging
                        log_for_debugging(f"[{label}] HTTP {resp.status}")
                    except Exception:
                        pass
                    return None
                data = await resp.json()
                events = data.get("data", [])
                if not isinstance(events, list):
                    events = []
                return {
                    "events": events,
                    "firstId": data.get("first_id"),
                    "hasMore": bool(data.get("has_more", False)),
                }
    except Exception as e:
        try:
            from ..utils.debug import log_for_debugging
            log_for_debugging(f"[{label}] error: {e}")
        except Exception:
            pass
        return None


async def fetchLatestEvents(
    ctx: HistoryAuthCtx,
    limit: int = HISTORY_PAGE_SIZE,
) -> Optional[HistoryPage]:
    """Newest page: last `limit` events, chronological, via anchor_to_latest.
    has_more=True means older events exist.
    """
    return await _fetch_page(
        ctx,
        {"limit": limit, "anchor_to_latest": True},
        "fetchLatestEvents",
    )


async def fetchOlderEvents(
    ctx: HistoryAuthCtx,
    before_id: str,
    limit: int = HISTORY_PAGE_SIZE,
) -> Optional[HistoryPage]:
    """Older page: events immediately before `before_id` cursor."""
    return await _fetch_page(
        ctx,
        {"limit": limit, "before_id": before_id},
        "fetchOlderEvents",
    )
