"""Core task helpers mirroring src/Task.ts."""

from __future__ import annotations

import os
import secrets
import time
from dataclasses import fields, is_dataclass
from typing import Any, Callable, Literal, Optional, Protocol

from .constants import TASK_ID_PREFIXES


TASK_ID_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


TaskStatus = Literal[
    "pending",
    "running",
    "completed",
    "failed",
    "killed",
]

TaskType = Literal[
    "local_bash",
    "local_agent",
    "remote_agent",
    "in_process_teammate",
    "local_workflow",
    "monitor_mcp",
    "dream",
]


class TaskHandle(Protocol):
    taskId: str
    cleanup: Optional[Callable[[], None]]


class TaskContext(Protocol):
    abortController: Any
    getAppState: Callable[[], Any]
    setAppState: Callable[[Callable[[Any], Any]], None]

SetAppState = Callable[[Callable[[Any], Any]], None]


class Task(Protocol):
    name: str
    type: str

    async def kill(self, task_id: str, setAppState: SetAppState) -> None: ...


def isTerminalTaskStatus(status: str) -> bool:
    return status in {"completed", "failed", "killed"}


def _task_output_path(task_id: str) -> str:
    try:
        from .utils.task.diskOutput import getTaskOutputPath

        path = getTaskOutputPath(task_id)
        if isinstance(path, str) and path:
            return path
    except Exception:
        pass

    return os.path.join(os.getcwd(), ".vivian", "tasks", f"{task_id}.log")


def generateTaskId(task_type: str, timestamp_ms: Optional[int] = None) -> str:
    del timestamp_ms
    prefix = TASK_ID_PREFIXES.get(task_type, "x")
    random_chars = "".join(
        TASK_ID_ALPHABET[secrets.randbelow(len(TASK_ID_ALPHABET))]
        for _ in range(8)
    )
    return f"{prefix}{random_chars}"


def _strip_unknown_fields(values: dict[str, Any], cls: type[Any]) -> dict[str, Any]:
    if not is_dataclass(cls):
        return values
    allowed = {field.name for field in fields(cls) if field.init}
    return {key: value for key, value in values.items() if key in allowed}


def createTaskStateBase(
    task_id: str,
    task_type: str,
    description: str,
    toolUseId: Optional[str] = None,
    cls: Optional[type[Any]] = None,
    **extra: Any,
) -> Any:
    payload = {
        "id": task_id,
        "type": task_type,
        "description": description,
        "status": extra.pop("status", "pending"),
        "tool_use_id": toolUseId,
        "start_time": extra.pop("start_time", time.time() * 1000),
        "end_time": extra.pop("end_time", None),
        "total_paused_ms": extra.pop("total_paused_ms", 0),
        "output_file": extra.pop("output_file", _task_output_path(task_id)),
        "output_offset": extra.pop("output_offset", 0),
        "notified": extra.pop("notified", False),
    }
    payload.update(extra)
    if cls is None:
        return payload
    return cls(**_strip_unknown_fields(payload, cls))


generate_task_id = generateTaskId
create_task_state_base = createTaskStateBase
is_terminal_task_status = isTerminalTaskStatus