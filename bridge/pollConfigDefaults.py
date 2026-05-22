"""Port of src/bridge/pollConfigDefaults.ts

Bridge poll interval defaults. Extracted so callers that don't need live
GrowthBook tuning can avoid the full dependency chain.
"""
from __future__ import annotations

from typing import TypedDict

# Poll interval when actively seeking work (no transport / below maxSessions).
POLL_INTERVAL_MS_NOT_AT_CAPACITY = 2000

# Poll interval when transport is connected.
POLL_INTERVAL_MS_AT_CAPACITY = 600_000

# Multisession bridge poll intervals
MULTISESSION_POLL_INTERVAL_MS_NOT_AT_CAPACITY = POLL_INTERVAL_MS_NOT_AT_CAPACITY
MULTISESSION_POLL_INTERVAL_MS_PARTIAL_CAPACITY = POLL_INTERVAL_MS_NOT_AT_CAPACITY
MULTISESSION_POLL_INTERVAL_MS_AT_CAPACITY = POLL_INTERVAL_MS_AT_CAPACITY


class PollIntervalConfig(TypedDict):
    poll_interval_ms_not_at_capacity: int
    poll_interval_ms_at_capacity: int
    non_exclusive_heartbeat_interval_ms: int
    multisession_poll_interval_ms_not_at_capacity: int
    multisession_poll_interval_ms_partial_capacity: int
    multisession_poll_interval_ms_at_capacity: int
    reclaim_older_than_ms: int
    session_keepalive_interval_v2_ms: int


DEFAULT_POLL_CONFIG: PollIntervalConfig = {
    "poll_interval_ms_not_at_capacity": POLL_INTERVAL_MS_NOT_AT_CAPACITY,
    "poll_interval_ms_at_capacity": POLL_INTERVAL_MS_AT_CAPACITY,
    # 0 = disabled. When > 0, at-capacity loops send per-work-item heartbeats.
    "non_exclusive_heartbeat_interval_ms": 0,
    "multisession_poll_interval_ms_not_at_capacity": MULTISESSION_POLL_INTERVAL_MS_NOT_AT_CAPACITY,
    "multisession_poll_interval_ms_partial_capacity": MULTISESSION_POLL_INTERVAL_MS_PARTIAL_CAPACITY,
    "multisession_poll_interval_ms_at_capacity": MULTISESSION_POLL_INTERVAL_MS_AT_CAPACITY,
    # Poll query param: reclaim unacknowledged work items older than this.
    "reclaim_older_than_ms": 5000,
    # 0 = disabled. When > 0, push a silent keep_alive frame.
    "session_keepalive_interval_v2_ms": 120_000,
}
