"""ExitPlanModeV2Tool — mirrors src/tools/ExitPlanModeTool/ExitPlanModeV2Tool.ts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from ...Tool import getEmptyToolPermissionContext, toolMatchesName
from ...bootstrap.state import (
    hasExitedPlanModeInSession,
    setHasExitedPlanMode,
    setNeedsPlanModeExitAttachment,
)
from ...utils.inProcessTeammateHelpers import (
    findInProcessTeammateTaskId,
    setAwaitingPlanApproval,
)
from ...utils.plans import getPlan, getPlanFilePath, persistFileSnapshotIfRemote
from ...utils.swarm.permissionSync import generateRequestId
from ...utils.teammate import getAgentName, getTeamName, isPlanModeRequired, isTeammate
from ...utils.teammateMailbox import writeToMailbox
from ..AgentTool.constants import AGENT_TOOL_NAME
from .constants import EXIT_PLAN_MODE_TOOL_NAME, EXIT_PLAN_MODE_V2_TOOL_NAME
from .prompt import DESCRIPTION, EXIT_PLAN_MODE_PROMPT


TOOL_NAME = EXIT_PLAN_MODE_V2_TOOL_NAME

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "allowedPrompts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "enum": ["Bash"]},
                    "prompt": {"type": "string"},
                },
            },
        },
        "plan": {
            "type": "string",
            "description": "The plan content injected from disk or edited by the user.",
        },
        "planFilePath": {
            "type": "string",
            "description": "The saved plan file path injected from disk.",
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "plan": {"type": ["string", "null"]},
        "isAgent": {"type": "boolean"},
        "filePath": {"type": "string"},
        "hasTaskTool": {"type": "boolean"},
        "planWasEdited": {"type": "boolean"},
        "awaitingLeaderApproval": {"type": "boolean"},
        "requestId": {"type": "string"},
    },
}


def _ctx_get(context: Any, key: str, default: Any = None) -> Any:
    if isinstance(context, dict):
        return context.get(key, default)
    return getattr(context, key, default)


def _ctx_call(context: Any, key: str, *args: Any, **kwargs: Any) -> Any:
    value = _ctx_get(context, key)
    if callable(value):
        return value(*args, **kwargs)
    return None


def _get_app_state(context: Any) -> Dict[str, Any]:
    state = _ctx_call(context, "getAppState")
    if isinstance(state, dict):
        return state
    if isinstance(context, dict) and isinstance(context.get("appState"), dict):
        return context["appState"]
    return {}


def _set_app_state_mode(context: Any, restore_mode: str) -> None:
    state = _get_app_state(context)
    tool_context = state.get("toolPermissionContext")
    if isinstance(tool_context, dict):
        tool_context["mode"] = restore_mode
        tool_context["prePlanMode"] = None
    if isinstance(context, dict) and isinstance(context.get("appState"), dict):
        context["appState"] = state
    setter = _ctx_get(context, "setAppState")
    if callable(setter):
        try:
            setter(lambda prev: {
                **(prev or {}),
                "toolPermissionContext": {
                    **((prev or {}).get("toolPermissionContext") or {}),
                    "mode": restore_mode,
                    "prePlanMode": None,
                },
            })
        except Exception:
            pass


async def description() -> str:
    return DESCRIPTION or "Prompts the user to exit plan mode and start coding"


async def prompt() -> str:
    return EXIT_PLAN_MODE_PROMPT


def isEnabled() -> bool:
    return True


def requiresUserInteraction() -> bool:
    return not isTeammate()


async def validateInput(_input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    if isTeammate():
        return {"result": True}
    mode = ((_get_app_state(context).get("toolPermissionContext") or {}).get("mode") or "default")
    if mode != "plan":
        return {
            "result": False,
            "message": (
                "You are not in plan mode. This tool is only for exiting plan mode after writing a plan. "
                "If your plan was already approved, continue with implementation."
            ),
            "errorCode": 1,
            "hasExitedPlanModeInSession": hasExitedPlanModeInSession(),
        }
    return {"result": True}


async def checkPermissions(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    if isTeammate():
        return {"behavior": "allow", "updatedInput": input_data}
    return {"behavior": "ask", "message": "Exit plan mode?", "updatedInput": input_data}


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Execute ExitPlanModeV2 using disk-backed plan storage."""
    agent_id = _ctx_get(context, "agentId")
    is_agent = bool(agent_id)
    file_path = getPlanFilePath(agent_id)
    input_plan = input_data.get("plan") if isinstance(input_data.get("plan"), str) else None
    plan = input_plan if input_plan is not None else getPlan(agent_id)

    if input_plan is not None:
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(input_plan)
        await persistFileSnapshotIfRemote()

    if isTeammate() and isPlanModeRequired():
        if not plan:
            raise ValueError(
                f"No plan file found at {file_path}. Please write your plan to this file before calling {EXIT_PLAN_MODE_TOOL_NAME}."
            )
        agent_name = getAgentName() or "unknown"
        team_name = getTeamName()
        request_id = generateRequestId().replace("perm-", "plan-")
        approval_request = {
            "type": "plan_approval_request",
            "from": agent_name,
            "timestamp": datetime.utcnow().isoformat(),
            "planFilePath": file_path,
            "planContent": plan,
            "requestId": request_id,
        }
        await writeToMailbox(
            "team-lead",
            {
                "from": agent_name,
                "text": __import__("json").dumps(approval_request),
                "timestamp": datetime.utcnow().isoformat(),
            },
            team_name,
        )
        app_state = _get_app_state(context)
        agent_task_id = findInProcessTeammateTaskId(agent_name, app_state)
        if agent_task_id:
            setter = _ctx_get(context, "setAppState")
            if callable(setter):
                setAwaitingPlanApproval(agent_task_id, setter, True)
        return {
            "data": {
                "plan": plan,
                "isAgent": True,
                "filePath": file_path,
                "awaitingLeaderApproval": True,
                "requestId": request_id,
            }
        }

    setHasExitedPlanMode(True)
    setNeedsPlanModeExitAttachment(True)
    app_state = _get_app_state(context)
    tool_permission_context = app_state.get("toolPermissionContext") or getEmptyToolPermissionContext()
    restore_mode = tool_permission_context.get("prePlanMode") or "default"
    _set_app_state_mode(context, restore_mode)

    tools = _ctx_get(context, "options", {})
    available_tools = tools.get("tools") if isinstance(tools, dict) else None
    has_task_tool = bool(
        isinstance(available_tools, list)
        and any(toolMatchesName(tool, AGENT_TOOL_NAME) for tool in available_tools)
    )

    return {
        "data": {
            "plan": plan,
            "isAgent": is_agent,
            "filePath": file_path,
            "hasTaskTool": has_task_tool or None,
            "planWasEdited": bool(input_plan is not None) or None,
        }
    }
