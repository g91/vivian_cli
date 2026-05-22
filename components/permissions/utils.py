"""Shared permission helper utilities."""

from __future__ import annotations

from typing import Any

from ...utils.env import getHostPlatformForAnalytics
from ...services.analytics.index import logEvent


def logUnaryPermissionEvent(
    completion_type: str,
    tool_use_confirm: Any,
    event: str,
    hasFeedback: bool | None = None,
) -> None:
    assistant_message = getattr(tool_use_confirm, "assistantMessage", None)
    message = getattr(assistant_message, "message", None)
    message_id = getattr(message, "id", None)
    if message_id is None and isinstance(tool_use_confirm, dict):
        assistant_message = tool_use_confirm.get("assistantMessage") or {}
        message = assistant_message.get("message") if isinstance(assistant_message, dict) else None
        if isinstance(message, dict):
            message_id = message.get("id")

    payload = {
        "event": event,
        "completion_type": completion_type,
        "language_name": "none",
        "message_id": message_id,
        "platform": getHostPlatformForAnalytics(),
    }
    if hasFeedback is not None:
        payload["hasFeedback"] = hasFeedback
    logEvent("tengu_unary_event", payload)


__all__ = ["logUnaryPermissionEvent"]