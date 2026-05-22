"""GrowthBook feature flags — mirrors src/services/analytics/growthbook.ts."""
from __future__ import annotations

import json
import os
from typing import Any, Optional

_client: Optional[dict] = None
_cache: dict[str, Any] = {}


def checkStatsigFeatureGate_CACHED_MAY_BE_STALE(gate_name: str) -> bool:
    """Check if a GrowthBook feature gate is enabled (uses cached value).

    Mirrors checkStatsigFeatureGate_CACHED_MAY_BE_STALE() from growthbook.ts.
    """
    try:
        from ...utils.config import get_global_config
        cfg = get_global_config()
        gb_cache = cfg.get("growthbookCache", {})
        result = gb_cache.get(gate_name)
        if isinstance(result, dict):
            return bool(result.get("on", False))
        return False
    except Exception:
        return False


def getDynamicConfig_CACHED_MAY_BE_STALE(config_name: str, default: Any = None) -> Any:
    """Get a GrowthBook dynamic config value (uses cached value).

    Mirrors getDynamicConfig_CACHED_MAY_BE_STALE() from growthbook.ts.
    """
    try:
        from ...utils.config import get_global_config
        cfg = get_global_config()
        gb_cache = cfg.get("growthbookCache", {})
        result = gb_cache.get(config_name)
        if result is not None and isinstance(result, dict):
            return result.get("value", default)
        return default
    except Exception:
        return default


def getFeatureValue_CACHED_MAY_BE_STALE(feature_name: str, default: Any = None) -> Any:
    """Get a GrowthBook feature value (uses cached value).

    Mirrors getFeatureValue_CACHED_MAY_BE_STALE() from growthbook.ts.
    """
    return getDynamicConfig_CACHED_MAY_BE_STALE(feature_name, default)


def getFeatureValue_CACHED_WITH_REFRESH(
    feature_name: str,
    default: Any = None,
    refresh_ms: int = 0,
) -> Any:
    """Python fallback for GrowthBook reads with refresh semantics.

    The current Python client reads from the persisted GrowthBook cache
    synchronously, so there is no separate refresh pipeline to coordinate here.
    Keep the API shape for parity and return the latest cached value directly.
    """
    del refresh_ms
    return getFeatureValue_CACHED_MAY_BE_STALE(feature_name, default)


def is1PEventLoggingEnabled() -> bool:
    """Check if first-party event logging is enabled."""
    try:
        from ...utils.privacyLevel import is_telemetry_disabled
        if is_telemetry_disabled():
            return False
    except Exception:
        pass
    return True


def logGrowthBookExperimentTo1P(experiment: str, variation: str) -> None:
    """Log a GrowthBook experiment exposure to 1P analytics."""
    if isAnalyticsDisabled():
        return
    try:
        from .firstPartyEventLogger import logEventTo1P

        logEventTo1P(
            "growthbook_exposure",
            {"experiment": experiment, "variation": variation},
        )
    except Exception:
        return


def initializeGrowthBook(attributes: dict) -> None:
    """Initialize the GrowthBook client with user attributes.

    Mirrors initializeGrowthBook() from growthbook.ts.
    """
    global _client, _cache
    _client = dict(attributes)
    _cache = dict(attributes)


def shutdownGrowthBook() -> None:
    """Shut down the GrowthBook client."""
    global _client, _cache
    _client = None
    _cache.clear()


# snake_case aliases
check_statsig_feature_gate_CACHED_MAY_BE_STALE = checkStatsigFeatureGate_CACHED_MAY_BE_STALE
get_dynamic_config_CACHED_MAY_BE_STALE = getDynamicConfig_CACHED_MAY_BE_STALE
get_feature_value_CACHED_MAY_BE_STALE = getFeatureValue_CACHED_MAY_BE_STALE
get_feature_value_CACHED_WITH_REFRESH = getFeatureValue_CACHED_WITH_REFRESH
initialize_growth_book = initializeGrowthBook
shutdown_growth_book = shutdownGrowthBook
