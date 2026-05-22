"""Analytics package — mirrors src/services/analytics/."""
from __future__ import annotations

from .config import isAnalyticsDisabled, isFeedbackSurveyDisabled
from .index import (
    AnalyticsSink,
    LogEventMetadata,
    attachAnalyticsSink,
    logEvent,
    logEventAsync,
    stripProtoFields,
    _resetForTesting,
)
from .sink import initializeAnalyticsSink, initializeAnalyticsGates
from .growthbook import (
    checkStatsigFeatureGate_CACHED_MAY_BE_STALE,
    getDynamicConfig_CACHED_MAY_BE_STALE,
    getFeatureValue_CACHED_MAY_BE_STALE,
    initializeGrowthBook,
    shutdownGrowthBook,
)
from .metadata import getEventMetadata
from .sinkKillswitch import isSinkKilled

__all__ = [
    "isAnalyticsDisabled",
    "isFeedbackSurveyDisabled",
    "AnalyticsSink",
    "LogEventMetadata",
    "attachAnalyticsSink",
    "logEvent",
    "logEventAsync",
    "stripProtoFields",
    "_resetForTesting",
    "initializeAnalyticsSink",
    "initializeAnalyticsGates",
    "checkStatsigFeatureGate_CACHED_MAY_BE_STALE",
    "getDynamicConfig_CACHED_MAY_BE_STALE",
    "getFeatureValue_CACHED_MAY_BE_STALE",
    "initializeGrowthBook",
    "shutdownGrowthBook",
    "getEventMetadata",
    "isSinkKilled",
]
