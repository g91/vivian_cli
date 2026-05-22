"""Compatibility wrapper for exact-case LocalShellTask modules."""

from __future__ import annotations

from .LocalShellTask.LocalShellTask import BACKGROUND_BASH_SUMMARY_PREFIX, LocalShellTask, looksLikePrompt, markTaskNotified
from .LocalShellTask.guards import BashTaskKind, LocalShellTaskState, isLocalShellTask


def is_local_shell_task(obj: object) -> bool:
    return isLocalShellTask(obj)


def looks_like_prompt(tail: str) -> bool:
    return looksLikePrompt(tail)


__all__ = [
    "BACKGROUND_BASH_SUMMARY_PREFIX",
    "BashTaskKind",
    "LocalShellTask",
    "LocalShellTaskState",
    "isLocalShellTask",
    "is_local_shell_task",
    "looksLikePrompt",
    "looks_like_prompt",
    "markTaskNotified",
]
