"""Analytics sink killswitch — mirrors src/services/analytics/sinkKillswitch.ts."""
from __future__ import annotations

from typing import Literal

SinkName = Literal["datadog", "firstParty"]

# Mangled name: per-sink analytics killswitch
SINK_KILLSWITCH_CONFIG_NAME = "tengu_frond_boric"


def isSinkKilled(sink: str) -> bool:
    """Check if an analytics sink has been killed via GrowthBook config.

    Mirrors isSinkKilled() from sinkKillswitch.ts.
    """
    try:
        from .growthbook import get_dynamic_config_CACHED_MAY_BE_STALE
        config = get_dynamic_config_CACHED_MAY_BE_STALE(SINK_KILLSWITCH_CONFIG_NAME, {})
        return config.get(sink) is True
    except Exception:
        return False


is_sink_killed = isSinkKilled
