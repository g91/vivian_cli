"""Analytics sink implementation — mirrors src/services/analytics/sink.ts."""
from __future__ import annotations

from .index import AnalyticsSink, LogEventMetadata, attachAnalyticsSink, stripProtoFields
from .sinkKillswitch import isSinkKilled

DATADOG_GATE_NAME = "tengu_log_datadog_events"

_is_datadog_gate_enabled: bool | None = None


def _should_track_datadog() -> bool:
    if isSinkKilled("datadog"):
        return False
    if _is_datadog_gate_enabled is not None:
        return _is_datadog_gate_enabled
    try:
        from .growthbook import check_statsig_feature_gate_CACHED_MAY_BE_STALE
        return check_statsig_feature_gate_CACHED_MAY_BE_STALE(DATADOG_GATE_NAME)
    except Exception:
        return False


def _log_event_impl(event_name: str, metadata: LogEventMetadata) -> None:
    try:
        from .firstPartyEventLogger import should_sample_event
        sample_result = should_sample_event(event_name)
    except Exception:
        sample_result = None

    if sample_result == 0:
        return

    metadata_with_sample = (
        {**metadata, "sample_rate": sample_result}
        if sample_result is not None and sample_result != 0
        else metadata
    )

    if _should_track_datadog():
        try:
            from .datadog import track_datadog_event
            track_datadog_event(event_name, stripProtoFields(metadata_with_sample))
        except Exception:
            pass

    try:
        from .firstPartyEventLogger import log_event_to_1p
        log_event_to_1p(event_name, metadata_with_sample)
    except Exception:
        pass


def _log_event_async_impl(event_name: str, metadata: LogEventMetadata) -> None:
    _log_event_impl(event_name, metadata)


class _AnalyticsSinkImpl(AnalyticsSink):
    def log_event(self, event_name: str, metadata: LogEventMetadata) -> None:
        _log_event_impl(event_name, metadata)

    def log_event_async(self, event_name: str, metadata: LogEventMetadata) -> None:
        _log_event_async_impl(event_name, metadata)


def initializeAnalyticsGates() -> None:
    """Initialize analytics gates during startup.

    Mirrors initializeAnalyticsGates() from sink.ts.
    """
    global _is_datadog_gate_enabled
    try:
        from .growthbook import check_statsig_feature_gate_CACHED_MAY_BE_STALE
        _is_datadog_gate_enabled = check_statsig_feature_gate_CACHED_MAY_BE_STALE(DATADOG_GATE_NAME)
    except Exception:
        _is_datadog_gate_enabled = False


def initializeAnalyticsSink() -> None:
    """Initialize the analytics sink.

    Call during app startup to attach the analytics backend.
    Idempotent: safe to call multiple times.

    Mirrors initializeAnalyticsSink() from sink.ts.
    """
    attachAnalyticsSink(_AnalyticsSinkImpl())


initialize_analytics_gates = initializeAnalyticsGates
initialize_analytics_sink = initializeAnalyticsSink
