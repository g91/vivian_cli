"""Compact background-task pill labels mirroring src/tasks/pillLabel.ts."""

from __future__ import annotations

from typing import Any, Iterable

from ..constants import DIAMOND_FILLED, DIAMOND_OPEN


def _field(task: Any, *names: str, default: Any = None) -> Any:
    if isinstance(task, dict):
        for name in names:
            if name in task:
                return task[name]
        return default
    for name in names:
        if hasattr(task, name):
            return getattr(task, name)
    return default


def getPillLabel(tasks: Iterable[Any]) -> str:
    task_list = list(tasks)
    if not task_list:
        return "0 background tasks"

    count = len(task_list)
    first_type = _field(task_list[0], "type")
    all_same_type = all(_field(task, "type") == first_type for task in task_list)

    if all_same_type:
        if first_type == "local_bash":
            monitors = sum(1 for task in task_list if _field(task, "kind") == "monitor")
            shells = count - monitors
            parts: list[str] = []
            if shells:
                parts.append("1 shell" if shells == 1 else f"{shells} shells")
            if monitors:
                parts.append("1 monitor" if monitors == 1 else f"{monitors} monitors")
            return ", ".join(parts)

        if first_type == "in_process_teammate":
            team_names = {
                _field(_field(task, "identity", default={}), "team_name", "teamName", default="")
                for task in task_list
            }
            team_names.discard("")
            team_count = len(team_names) or 1
            return "1 team" if team_count == 1 else f"{team_count} teams"

        if first_type == "local_agent":
            return "1 local agent" if count == 1 else f"{count} local agents"

        if first_type == "remote_agent":
            first = task_list[0]
            if count == 1 and _field(first, "is_ultraplan", "isUltraplan", default=False):
                phase = _field(first, "ultraplan_phase", "ultraplanPhase")
                if phase == "plan_ready":
                    return f"{DIAMOND_FILLED} ultraplan ready"
                if phase == "needs_input":
                    return f"{DIAMOND_OPEN} ultraplan needs your input"
                return f"{DIAMOND_OPEN} ultraplan"
            return f"{DIAMOND_OPEN} 1 cloud session" if count == 1 else f"{DIAMOND_OPEN} {count} cloud sessions"

        if first_type == "local_workflow":
            return "1 background workflow" if count == 1 else f"{count} background workflows"

        if first_type == "monitor_mcp":
            return "1 monitor" if count == 1 else f"{count} monitors"

        if first_type == "dream":
            return "dreaming"

    return f"{count} background task" if count == 1 else f"{count} background tasks"


def pillNeedsCta(tasks: Iterable[Any]) -> bool:
    task_list = list(tasks)
    if len(task_list) != 1:
        return False
    task = task_list[0]
    return (
        _field(task, "type") == "remote_agent"
        and _field(task, "is_ultraplan", "isUltraplan", default=False) is True
        and _field(task, "ultraplan_phase", "ultraplanPhase") is not None
    )