"""
Port of src/utils/task/sdkProgress.ts
"""
from __future__ import annotations

from typing import Any
import time

from ..sdkEventQueue import enqueueSdkEvent


def emitTaskProgress(params: dict[str, Any] | None = None) -> None:
    """Emit a `task_progress` SDK event. Shared by background agents (per tool_use
in runAsyncAgentLifecycle) and workflows (per flushProgress batch). Accepts
already-computed primitives so callers can derive them from their own state
shapes (ProgressTracker for agents, LocalWorkflowTaskState for workflows)."""
    params = params or {}
    enqueueSdkEvent(
        {
            "type": "system",
            "subtype": "task_progress",
            "task_id": params.get("taskId"),
            "tool_use_id": params.get("toolUseId"),
            "description": params.get("description", ""),
            "usage": {
                "total_tokens": params.get("totalTokens", 0),
                "tool_uses": params.get("toolUses", 0),
                "duration_ms": int(time.time() * 1000) - int(params.get("startTime", 0) or 0),
            },
            "last_tool_name": params.get("lastToolName"),
            "summary": params.get("summary"),
            "workflow_progress": params.get("workflowProgress"),
        }
    )


emit_task_progress = emitTaskProgress

