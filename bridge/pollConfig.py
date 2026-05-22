"""Port of src/bridge/pollConfig.ts

Bridge poll interval config fetched from GrowthBook with schema validation.
Falls back to DEFAULT_POLL_CONFIG when the flag is absent/malformed.
"""
from __future__ import annotations

from .pollConfigDefaults import DEFAULT_POLL_CONFIG, PollIntervalConfig


def getPollIntervalConfig() -> PollIntervalConfig:
    """
    Fetch the bridge poll interval config from GrowthBook.
    Validates against constraints; falls back to defaults if invalid.
    """
    try:
        from ..services.analytics.growthbook import get_feature_value_cached_with_refresh
        raw = get_feature_value_cached_with_refresh(
            "tengu_bridge_poll_interval_config",
            DEFAULT_POLL_CONFIG,
            5 * 60 * 1000,
        )
        if not isinstance(raw, dict):
            return DEFAULT_POLL_CONFIG
        return _validate_poll_config(raw)
    except Exception:
        return DEFAULT_POLL_CONFIG


def _validate_poll_config(raw: dict) -> PollIntervalConfig:
    """Validate raw config dict against constraints. Returns default on any violation."""
    try:
        cfg = dict(DEFAULT_POLL_CONFIG)
        cfg.update({k: v for k, v in raw.items() if k in DEFAULT_POLL_CONFIG})

        def zero_or_at_least(v: int, minimum: int = 100) -> bool:
            return v == 0 or v >= minimum

        if cfg["poll_interval_ms_not_at_capacity"] < 100:
            return DEFAULT_POLL_CONFIG
        if not zero_or_at_least(cfg["poll_interval_ms_at_capacity"]):
            return DEFAULT_POLL_CONFIG
        if cfg["non_exclusive_heartbeat_interval_ms"] < 0:
            return DEFAULT_POLL_CONFIG
        if cfg["multisession_poll_interval_ms_not_at_capacity"] < 100:
            return DEFAULT_POLL_CONFIG
        if cfg["multisession_poll_interval_ms_partial_capacity"] < 100:
            return DEFAULT_POLL_CONFIG
        if not zero_or_at_least(cfg["multisession_poll_interval_ms_at_capacity"]):
            return DEFAULT_POLL_CONFIG
        if cfg["reclaim_older_than_ms"] < 1:
            return DEFAULT_POLL_CONFIG
        if cfg["session_keepalive_interval_v2_ms"] < 0:
            return DEFAULT_POLL_CONFIG

        # At-capacity liveness: need heartbeat OR poll
        hb = cfg["non_exclusive_heartbeat_interval_ms"]
        at_cap = cfg["poll_interval_ms_at_capacity"]
        ms_at_cap = cfg["multisession_poll_interval_ms_at_capacity"]
        if hb == 0 and at_cap == 0:
            return DEFAULT_POLL_CONFIG
        if hb == 0 and ms_at_cap == 0:
            return DEFAULT_POLL_CONFIG

        return PollIntervalConfig(**cfg)  # type: ignore[call-arg]
    except Exception:
        return DEFAULT_POLL_CONFIG
