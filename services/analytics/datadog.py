"""Datadog event tracking — mirrors src/services/analytics/datadog.ts."""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import urllib.request
from typing import Any

from .config import isAnalyticsDisabled

DATADOG_LOGS_ENDPOINT = "https://http-intake.logs.us5.datadoghq.com/api/v2/logs"
DATADOG_CLIENT_TOKEN = "pubbbf48e6d78dae54bceaa4acf463299bf"
DEFAULT_FLUSH_INTERVAL_MS = 15000
MAX_BATCH_SIZE = 100
NETWORK_TIMEOUT_MS = 5000

DATADOG_ALLOWED_EVENTS = frozenset([
    "chrome_bridge_connection_succeeded",
    "chrome_bridge_connection_failed",
    "chrome_bridge_disconnected",
    "chrome_bridge_tool_call_completed",
    "chrome_bridge_tool_call_error",
    "chrome_bridge_tool_call_started",
    "chrome_bridge_tool_call_timeout",
    "tengu_api_error",
    "tengu_api_success",
    "tengu_brief_mode_enabled",
    "tengu_brief_mode_toggled",
    "tengu_brief_send",
    "tengu_cancel",
    "tengu_compact_failed",
    "tengu_exit",
    "tengu_flicker",
    "tengu_init",
    "tengu_model_fallback_triggered",
    "tengu_oauth_error",
    "tengu_oauth_success",
    "tengu_oauth_token_refresh_failure",
    "tengu_oauth_token_refresh_success",
    "tengu_oauth_token_refresh_lock_acquiring",
    "tengu_oauth_token_refresh_lock_acquired",
    "tengu_oauth_token_refresh_starting",
    "tengu_oauth_token_refresh_completed",
    "tengu_oauth_token_refresh_lock_releasing",
    "tengu_oauth_token_refresh_lock_released",
    "tengu_query_error",
    "tengu_session_file_read",
    "tengu_started",
    "tengu_tool_use_error",
    "tengu_tool_use_granted_in_prompt_permanent",
    "tengu_tool_use_granted_in_prompt_temporary",
    "tengu_tool_use_rejected_in_prompt",
    "tengu_tool_use_success",
    "tengu_uncaught_exception",
    "tengu_unhandled_rejection",
    "tengu_voice_recording_started",
    "tengu_voice_toggled",
    "tengu_team_mem_sync_pull",
    "tengu_team_mem_sync_push",
    "tengu_team_mem_sync_started",
    "tengu_team_mem_entries_capped",
])

_batch: list[dict] = []
_batch_lock = threading.Lock()
_flush_timer: threading.Timer | None = None


def trackDatadogEvent(event_name: str, metadata: dict) -> None:
    """Queue a Datadog event for batched sending.

    Mirrors trackDatadogEvent() from datadog.ts.
    """
    if isAnalyticsDisabled():
        return
    if event_name not in DATADOG_ALLOWED_EVENTS:
        return

    try:
        from .metadata import get_event_metadata
        enriched = {**get_event_metadata(), **metadata, "event": event_name}
    except Exception:
        enriched = {**metadata, "event": event_name}

    with _batch_lock:
        _batch.append(enriched)
        if len(_batch) >= MAX_BATCH_SIZE:
            _flush()
        else:
            _schedule_flush()


def _schedule_flush() -> None:
    global _flush_timer
    if _flush_timer is None:
        _flush_timer = threading.Timer(DEFAULT_FLUSH_INTERVAL_MS / 1000, _flush_and_reset)
        _flush_timer.daemon = True
        _flush_timer.start()


def _flush_and_reset() -> None:
    global _flush_timer
    with _batch_lock:
        _flush_timer = None
        _flush()


def _flush() -> None:
    """Send queued events to Datadog."""
    if not _batch:
        return
    events = list(_batch)
    _batch.clear()
    try:
        data = json.dumps(events).encode()
        req = urllib.request.Request(
            DATADOG_LOGS_ENDPOINT,
            data=data,
            headers={
                "Content-Type": "application/json",
                "DD-API-KEY": DATADOG_CLIENT_TOKEN,
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=NETWORK_TIMEOUT_MS / 1000)
    except Exception:
        pass


track_datadog_event = trackDatadogEvent
