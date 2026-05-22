"""Port of src/utils/sdkEventQueue.ts."""

from __future__ import annotations

from typing import Any, Dict
import uuid

from ..bootstrap.state import getIsNonInteractiveSession, getSessionId


TaskStartedEvent = Dict[str, Any]
TaskProgressEvent = Dict[str, Any]
TaskNotificationSdkEvent = Dict[str, Any]
SessionStateChangedEvent = Dict[str, Any]
SdkEvent = Any


MAX_QUEUE_SIZE = 1000
queue: list[SdkEvent] = []


def enqueueSdkEvent(event):
    if not getIsNonInteractiveSession():
        return
    if len(queue) >= MAX_QUEUE_SIZE:
        queue.pop(0)
    queue.append(event)


def drainSdkEvents():
    if not queue:
        return []
    events = list(queue)
    queue.clear()
    return [
        {
            **event,
            "uuid": str(uuid.uuid4()),
            "session_id": getSessionId(),
        }
        for event in events
    ]


def emitTaskTerminatedSdk(taskId, status, opts=None):
    """Emit a task_notification SDK event for a task reaching a terminal state."""
    opts = opts or {}
    enqueueSdkEvent(
        {
            "type": "system",
            "subtype": "task_notification",
            "task_id": taskId,
            "tool_use_id": opts.get("toolUseId"),
            "status": status,
            "output_file": opts.get("outputFile", ""),
            "summary": opts.get("summary", ""),
            "usage": opts.get("usage"),
        }
    )

