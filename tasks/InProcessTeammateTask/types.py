"""In-process teammate task types mirroring src/tasks/InProcessTeammateTask/types.ts."""

from __future__ import annotations

from typing import Any, Iterable, TypeVar

from ..types import InProcessTeammateTaskState, TeammateIdentity


TEAMMATE_MESSAGES_UI_CAP = 50
T = TypeVar("T")


def isInProcessTeammateTask(task: Any) -> bool:
    return (task.get("type") if isinstance(task, dict) else getattr(task, "type", None)) == "in_process_teammate"


def appendCappedMessage(prev: Iterable[T] | None, item: T) -> list[T]:
    previous = list(prev or [])
    if not previous:
        return [item]
    if len(previous) >= TEAMMATE_MESSAGES_UI_CAP:
        previous = previous[-(TEAMMATE_MESSAGES_UI_CAP - 1):]
    return [*previous, item]