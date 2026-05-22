"""Port of src/utils/telemetry/events.ts."""
from __future__ import annotations

import datetime as _dt
import os
from typing import Any

from ...bootstrap.state import getEventLogger, getPromptId
from ..debug import logForDebugging
from ..envUtils import is_env_truthy
from ..telemetryAttributes import getTelemetryAttributes


eventSequence = 0
hasWarnedNoEventLogger = False


def isUserPromptLoggingEnabled():
    return is_env_truthy(os.environ.get("OTEL_LOG_USER_PROMPTS", ""))


def redactIfDisabled(content):
    return content if isUserPromptLoggingEnabled() else "<REDACTED>"


async def logOTelEvent(eventName, metadata=None):
    global eventSequence, hasWarnedNoEventLogger

    eventLogger = getEventLogger()
    if not eventLogger:
        if not hasWarnedNoEventLogger:
            hasWarnedNoEventLogger = True
            logForDebugging(
                f"[3P telemetry] Event dropped (no event logger initialized): {eventName}",
                level="warn",
            )
        return

    if os.environ.get("NODE_ENV") == "test":
        return

    attributes: dict[str, Any] = {
        **getTelemetryAttributes(),
        "event.name": eventName,
        "event.timestamp": _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "event.sequence": eventSequence,
    }
    eventSequence += 1

    promptId = getPromptId()
    if promptId:
        attributes["prompt.id"] = promptId

    workspaceHostPaths = os.environ.get("vivian_CODE_WORKSPACE_HOST_PATHS")
    if workspaceHostPaths:
        attributes["workspace.host_paths"] = workspaceHostPaths.split("|")

    for key, value in dict(metadata or {}).items():
        if value is not None:
            attributes[key] = value

    payload = {
        "body": f"vivian_code.{eventName}",
        "attributes": attributes,
    }

    emit = getattr(eventLogger, "emit", None)
    if callable(emit):
        emit(payload)


is_user_prompt_logging_enabled = isUserPromptLoggingEnabled
redact_if_disabled = redactIfDisabled
log_otel_event = logOTelEvent

