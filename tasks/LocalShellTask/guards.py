"""Local shell task guards mirroring src/tasks/LocalShellTask/guards.ts."""

from __future__ import annotations

from typing import Any, Literal

from ..types import LocalShellTaskState


BashTaskKind = Literal["bash", "monitor"]


def isLocalShellTask(task: Any) -> bool:
    if isinstance(task, dict):
        return task.get("type") == "local_bash"
    return getattr(task, "type", None) == "local_bash"