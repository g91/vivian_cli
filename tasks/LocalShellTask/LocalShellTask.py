"""Local shell task helpers mirroring src/tasks/LocalShellTask/LocalShellTask.tsx."""

from __future__ import annotations

import re
import time
from dataclasses import is_dataclass, replace
from typing import Any, Callable

from ...utils.task.framework import PANEL_GRACE_MS, updateTaskState


BACKGROUND_BASH_SUMMARY_PREFIX = "Background bash:"

PROMPT_PATTERNS = [
    re.compile(r"\(y/n\)", re.IGNORECASE),
    re.compile(r"\[y/n\]", re.IGNORECASE),
    re.compile(r"\(yes/no\)", re.IGNORECASE),
    re.compile(r"\b(?:Do you|Would you|Shall I|Are you sure|Ready to)\b.*\?\s*$", re.IGNORECASE),
    re.compile(r"Press (any key|Enter)", re.IGNORECASE),
    re.compile(r"Continue\?", re.IGNORECASE),
    re.compile(r"Overwrite\?", re.IGNORECASE),
]


def looksLikePrompt(tail: str) -> bool:
    last_line = tail.rstrip().rsplit("\n", 1)[-1]
    return any(pattern.search(last_line) for pattern in PROMPT_PATTERNS)


def _replace_task(task: Any, **updates: Any) -> Any:
    if isinstance(task, dict):
        merged = dict(task)
        merged.update(updates)
        return merged
    if is_dataclass(task):
        return replace(task, **updates)
    for key, value in updates.items():
        setattr(task, key, value)
    return task


def markTaskNotified(taskId: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    updateTaskState(taskId, setAppState, lambda task: task if getattr(task, "notified", False) else _replace_task(task, notified=True))


class _LocalShellTaskImpl:
    name = "LocalShellTask"
    type = "local_bash"

    async def kill(self, taskId: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
        def _kill(task: Any) -> Any:
            if getattr(task, "status", None) != "running":
                return task
            process = getattr(task, "_process", None)
            if process is not None:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
            cleanup = getattr(task, "unregister_cleanup", None)
            if callable(cleanup):
                cleanup()
            evict_after = time.time() * 1000 + PANEL_GRACE_MS
            return _replace_task(
                task,
                status="killed",
                end_time=time.time() * 1000,
                unregister_cleanup=None,
                cleanup_timeout_id=None,
                is_backgrounded=True,
                evict_after=evict_after,
            )

        updateTaskState(taskId, setAppState, _kill)


LocalShellTask = _LocalShellTaskImpl()