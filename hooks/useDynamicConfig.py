"""Port of src/hooks/useDynamicConfig.ts."""
from __future__ import annotations

from typing import TypeVar

from ..services.analytics.growthbook import getDynamicConfig_CACHED_MAY_BE_STALE

T = TypeVar('T')


def useDynamicConfig(configName: str, defaultValue: T) -> T:
    return getDynamicConfig_CACHED_MAY_BE_STALE(configName, defaultValue)
