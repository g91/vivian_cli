"""Analytics index — public API for event logging.

Mirrors src/services/analytics/index.ts.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

# ---------------------------------------------------------------------------
# Marker types (Python equivalents as type aliases)
# ---------------------------------------------------------------------------

AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS = None  # type: ignore
AnalyticsMetadata_I_VERIFIED_THIS_IS_PII_TAGGED = None  # type: ignore


def stripProtoFields(metadata: dict) -> dict:
    """Strip _PROTO_* keys from a payload destined for general-access storage.

    Returns the input unchanged when no _PROTO_ keys present.
    Mirrors stripProtoFields() from analytics/index.ts.
    """
    result: Optional[dict] = None
    for key in metadata:
        if key.startswith("_PROTO_"):
            if result is None:
                result = dict(metadata)
            del result[key]  # type: ignore
    return result if result is not None else metadata


# ---------------------------------------------------------------------------
# Internal types
# ---------------------------------------------------------------------------

LogEventMetadata = dict  # {str: bool|int|float|None}

_QueuedEvent = dict  # {eventName, metadata, async_}


class AnalyticsSink:
    """Sink interface for the analytics backend."""

    def log_event(self, event_name: str, metadata: LogEventMetadata) -> None:
        del event_name, metadata
        return None

    def log_event_async(self, event_name: str, metadata: LogEventMetadata) -> None:
        self.log_event(event_name, metadata)


# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_event_queue: list[_QueuedEvent] = []
_sink: Optional[AnalyticsSink] = None


def attachAnalyticsSink(new_sink: AnalyticsSink) -> None:
    """Attach the analytics sink that will receive all events.

    Queued events are drained synchronously.
    Idempotent — safe to call multiple times.

    Mirrors attachAnalyticsSink() from analytics/index.ts.
    """
    global _sink
    if _sink is not None:
        return
    _sink = new_sink

    if _event_queue:
        import os
        queued = list(_event_queue)
        _event_queue.clear()

        if os.environ.get("USER_TYPE") == "ant":
            _sink.log_event("analytics_sink_attached", {"queued_event_count": len(queued)})

        for ev in queued:
            if ev.get("async_"):
                _sink.log_event_async(ev["eventName"], ev["metadata"])
            else:
                _sink.log_event(ev["eventName"], ev["metadata"])


def logEvent(event_name: str, metadata: LogEventMetadata) -> None:
    """Log an event to analytics backends (synchronous).

    If no sink is attached, events are queued and drained when the sink attaches.
    Mirrors logEvent() from analytics/index.ts.
    """
    if _sink is None:
        _event_queue.append({"eventName": event_name, "metadata": metadata, "async_": False})
        return
    _sink.log_event(event_name, metadata)


def logEventAsync(event_name: str, metadata: LogEventMetadata) -> None:
    """Log an event to analytics backends (asynchronous).

    Mirrors logEventAsync() from analytics/index.ts.
    """
    if _sink is None:
        _event_queue.append({"eventName": event_name, "metadata": metadata, "async_": True})
        return
    _sink.log_event_async(event_name, metadata)


def _resetForTesting() -> None:
    """Reset analytics state for testing purposes only."""
    global _sink
    _sink = None
    _event_queue.clear()


# Convenience alias matching TS name
log_event = logEvent
log_event_async = logEventAsync
attach_analytics_sink = attachAnalyticsSink
strip_proto_fields = stripProtoFields
