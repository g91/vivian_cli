"""First-party event logger — mirrors src/services/analytics/firstPartyEventLogger.ts."""
from __future__ import annotations

import os
import random
from typing import Any, Optional

from .config import isAnalyticsDisabled
from .growthbook import getDynamicConfig_CACHED_MAY_BE_STALE, is1PEventLoggingEnabled

EVENT_SAMPLING_CONFIG_NAME = "tengu_event_sampling_config"


def getEventSamplingConfig() -> dict:
    """Get the event sampling configuration from GrowthBook."""
    return getDynamicConfig_CACHED_MAY_BE_STALE(EVENT_SAMPLING_CONFIG_NAME, {})


def shouldSampleEvent(event_name: str) -> Optional[int]:
    """Determine if an event should be sampled based on its sample rate.

    Returns the sample_rate if event should be logged, 0 if dropped, None if unsampled.
    Mirrors shouldSampleEvent() from firstPartyEventLogger.ts.
    """
    config = getEventSamplingConfig()
    event_config = config.get(event_name)
    if not event_config:
        return None
    sample_rate = event_config.get("sample_rate", 1.0)
    if random.random() < sample_rate:
        return int(sample_rate * 100)
    return 0


def logEventTo1P(event_name: str, metadata: dict) -> None:
    """Log event to the first-party event logging system.

    Mirrors logEventTo1P() from firstPartyEventLogger.ts.
    """
    if isAnalyticsDisabled():
        return
    if not is1PEventLoggingEnabled():
        return
    try:
        from .firstPartyEventLoggingExporter import export_event
        export_event(event_name, metadata)
    except Exception:
        pass


def initializeFirstPartyEventLogging() -> None:
    """Initialize the first-party event logging system."""
    if isAnalyticsDisabled():
        return
    if not is1PEventLoggingEnabled():
        return
    try:
        from .firstPartyEventLoggingExporter import FirstPartyEventLoggingExporter

        FirstPartyEventLoggingExporter()
    except Exception:
        return


should_sample_event = shouldSampleEvent
log_event_to_1p = logEventTo1P
initialize_first_party_event_logging = initializeFirstPartyEventLogging
