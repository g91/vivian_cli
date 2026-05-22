"""Port of src/utils/teammate.ts."""
from __future__ import annotations

import asyncio
import os
from typing import Any

from .envUtils import is_env_truthy
from .teammateContext import getTeammateContext


_dynamic_team_context: dict[str, Any] | None = None


def getParentSessionId() -> str | None:
    in_process_ctx = getTeammateContext()
    if in_process_ctx:
        return in_process_ctx.get("parentSessionId")
    return (_dynamic_team_context or {}).get("parentSessionId")


def setDynamicTeamContext(context=None) -> None:
    global _dynamic_team_context
    _dynamic_team_context = dict(context) if context is not None else None


def clearDynamicTeamContext() -> None:
    global _dynamic_team_context
    _dynamic_team_context = None


def getDynamicTeamContext():
    return _dynamic_team_context


def getAgentId() -> str | None:
    in_process_ctx = getTeammateContext()
    if in_process_ctx:
        return in_process_ctx.get("agentId")
    return (_dynamic_team_context or {}).get("agentId")


def getAgentName() -> str | None:
    in_process_ctx = getTeammateContext()
    if in_process_ctx:
        return in_process_ctx.get("agentName")
    return (_dynamic_team_context or {}).get("agentName")


def getTeamName(teamContext=None) -> str | None:
    in_process_ctx = getTeammateContext()
    if in_process_ctx:
        return in_process_ctx.get("teamName")
    if (_dynamic_team_context or {}).get("teamName"):
        return (_dynamic_team_context or {}).get("teamName")
    if isinstance(teamContext, dict):
        return teamContext.get("teamName")
    return getattr(teamContext, "teamName", None)


def isTeammate() -> bool:
    in_process_ctx = getTeammateContext()
    if in_process_ctx:
        return True
    return bool((_dynamic_team_context or {}).get("agentId") and (_dynamic_team_context or {}).get("teamName"))


def getTeammateColor() -> str | None:
    in_process_ctx = getTeammateContext()
    if in_process_ctx:
        return in_process_ctx.get("color")
    return (_dynamic_team_context or {}).get("color")


def isPlanModeRequired() -> bool:
    in_process_ctx = getTeammateContext()
    if in_process_ctx:
        return bool(in_process_ctx.get("planModeRequired"))
    if _dynamic_team_context is not None:
        return bool(_dynamic_team_context.get("planModeRequired"))
    return is_env_truthy(os.environ.get("vivian_CODE_PLAN_MODE_REQUIRED"))


def isTeamLead(teamContext) -> bool:
    lead_agent_id = None
    if isinstance(teamContext, dict):
        lead_agent_id = teamContext.get("leadAgentId")
    else:
        lead_agent_id = getattr(teamContext, "leadAgentId", None)
    if not lead_agent_id:
        return False

    my_agent_id = getAgentId()
    if my_agent_id == lead_agent_id:
        return True
    if not my_agent_id:
        return True
    return False


def hasActiveInProcessTeammates(appState) -> bool:
    tasks = _tasks_dict(appState)
    for task in tasks.values():
        if _task_get(task, "type") == "in_process_teammate" and _task_get(task, "status") == "running":
            return True
    return False


def hasWorkingInProcessTeammates(appState) -> bool:
    tasks = _tasks_dict(appState)
    for task in tasks.values():
        if (
            _task_get(task, "type") == "in_process_teammate"
            and _task_get(task, "status") == "running"
            and not bool(_task_get(task, "isIdle"))
        ):
            return True
    return False


def waitForTeammatesToBecomeIdle(setAppState, appState=None):
    """Return an awaitable that resolves once working teammates become idle."""

    async def _wait() -> None:
        if appState is not None and not callable(appState) and not hasWorkingInProcessTeammates(appState):
            return
        while True:
            current_state = appState() if callable(appState) else appState
            if current_state is None:
                return
            if not hasWorkingInProcessTeammates(current_state):
                return
            await asyncio.sleep(0.05)

    _ = setAppState
    return _wait()


def _tasks_dict(app_state: Any) -> dict[str, Any]:
    if isinstance(app_state, dict):
        value = app_state.get("tasks", {})
    else:
        value = getattr(app_state, "tasks", {})
    return value if isinstance(value, dict) else {}


def _task_get(task: Any, key: str):
    if isinstance(task, dict):
        return task.get(key)
    return getattr(task, key, None)


get_parent_session_id = getParentSessionId
set_dynamic_team_context = setDynamicTeamContext
clear_dynamic_team_context = clearDynamicTeamContext
get_dynamic_team_context = getDynamicTeamContext
get_agent_id = getAgentId
get_agent_name = getAgentName
get_team_name = getTeamName
is_teammate = isTeammate
get_teammate_color = getTeammateColor
is_plan_mode_required = isPlanModeRequired
is_team_lead = isTeamLead
has_active_in_process_teammates = hasActiveInProcessTeammates
has_working_in_process_teammates = hasWorkingInProcessTeammates
wait_for_teammates_to_become_idle = waitForTeammatesToBecomeIdle
