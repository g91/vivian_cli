"""Time-based microcompact config — mirrors src/services/compact/timeBasedMCConfig.ts."""
from __future__ import annotations

from dataclasses import dataclass

TIME_BASED_MC_CONFIG_DEFAULTS: dict = {
    "enabled": False,
    "gapThresholdMinutes": 60,
    "keepRecent": 5,
}

TimeBasedMCConfig = dict


def getTimeBasedMCConfig() -> TimeBasedMCConfig:
    """Get the GrowthBook config for time-based microcompact.

    Mirrors getTimeBasedMCConfig() from timeBasedMCConfig.ts.
    """
    try:
        from ..analytics.growthbook import getFeatureValue_CACHED_MAY_BE_STALE
        return getFeatureValue_CACHED_MAY_BE_STALE(
            "tengu_slate_heron",
            TIME_BASED_MC_CONFIG_DEFAULTS,
        )
    except Exception:
        return dict(TIME_BASED_MC_CONFIG_DEFAULTS)


get_time_based_mc_config = getTimeBasedMCConfig
