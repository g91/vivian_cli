"""First-party event logging exporter — mirrors src/services/analytics/firstPartyEventLoggingExporter.ts."""
from __future__ import annotations

import logging
from typing import Any

_EXPORTED_EVENTS: list[dict[str, Any]] = []
logger = logging.getLogger(__name__)


def export_event(event_name: str, metadata: dict) -> None:
    """Export an event to the first-party event logging system.

    Mirrors FirstPartyEventLoggingExporter from firstPartyEventLoggingExporter.ts.
    """
    _EXPORTED_EVENTS.append({"event_name": event_name, "metadata": dict(metadata)})
    logger.debug("1P event %s %s", event_name, metadata)


class FirstPartyEventLoggingExporter:
    """OTEL log record exporter that sends events to the 1P event logging system."""

    def export(self, records: list) -> None:
        for record in records:
            if isinstance(record, dict):
                export_event(str(record.get("event_name", "unknown")), dict(record.get("metadata") or {}))
            else:
                export_event("unknown", {"record": str(record)})

    def shutdown(self) -> None:
        return None
