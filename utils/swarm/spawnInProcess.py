"""Port of src/utils/swarm/spawnInProcess.ts."""
from __future__ import annotations

import random
import time

from ...Task import createTaskStateBase, generateTaskId
from ...bootstrap.state import getSessionId
from ...constants.spinnerVerbs import getSpinnerVerbs
from ...constants.turnCompletionVerbs import TURN_COMPLETION_VERBS
from ..abortController import create_abort_controller
from ..agentId import format_agent_id
from ..cleanupRegistry import register_cleanup
from ..debug import logForDebugging
from ..sdkEventQueue import emitTaskTerminatedSdk
from ..task.diskOutput import evictTaskOutput
from ..task.framework import registerTask
from ..teammateContext import createTeammateContext
from .teamHelpers import removeMemberByAgentId


SetAppStateFn = object
SpawnContext = dict[str, object]
InProcessSpawnConfig = dict[str, object]
InProcessSpawnOutput = dict[str, object]


async def spawnInProcessTeammate(config, context):
    name = _cfg(config, "name")
    team_name = _cfg(config, "teamName")
    prompt = _cfg(config, "prompt") or ""
    color = _cfg(config, "color")
    plan_mode_required = bool(_cfg(config, "planModeRequired"))
    model = _cfg(config, "model")
    set_app_state = _cfg(context, "setAppState")

    agent_id = format_agent_id(name, team_name)
    task_id = generateTaskId("in_process_teammate")
    logForDebugging(f"[spawnInProcessTeammate] Spawning {agent_id} (taskId: {task_id})")

    try:
        perfetto_enabled, perfetto_register, _ = _get_perfetto_hooks()

        abort_controller = create_abort_controller()
        parent_session_id = getSessionId()
        identity = {
            "agentId": agent_id,
            "agentName": name,
            "teamName": team_name,
            "color": color,
            "planModeRequired": plan_mode_required,
            "parentSessionId": parent_session_id,
        }
        teammate_context = createTeammateContext(
            {
                "agentId": agent_id,
                "agentName": name,
                "teamName": team_name,
                "color": color,
                "planModeRequired": plan_mode_required,
                "parentSessionId": parent_session_id,
                "abortController": abort_controller,
            }
        )

        if perfetto_enabled():
            perfetto_register(agent_id, name, parent_session_id)

        description = f"{name}: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
        spinner_verbs = getSpinnerVerbs() or ["Working"]
        completion_verbs = TURN_COMPLETION_VERBS or ["Finished"]
        task_state = createTaskStateBase(
            task_id,
            "in_process_teammate",
            description,
            _cfg(context, "toolUseId"),
            status="running",
        )
        task_state.update(
            {
                "type": "in_process_teammate",
                "status": "running",
                "identity": identity,
                "prompt": prompt,
                "model": model,
                "abortController": abort_controller,
                "awaitingPlanApproval": False,
                "spinnerVerb": random.choice(spinner_verbs),
                "pastTenseVerb": random.choice(completion_verbs),
                "permissionMode": "plan" if plan_mode_required else "default",
                "isIdle": False,
                "shutdownRequested": False,
                "lastReportedToolCount": 0,
                "lastReportedTokenCount": 0,
                "pendingUserMessages": [],
                "messages": [],
                "toolUseId": _cfg(context, "toolUseId"),
                "startTime": time.time() * 1000,
            }
        )

        async def _cleanup() -> None:
            logForDebugging(f"[spawnInProcessTeammate] Cleanup called for {agent_id}")
            abort_controller.abort()

        unregister_cleanup = register_cleanup(_cleanup)
        task_state["unregisterCleanup"] = unregister_cleanup

        registerTask(task_state, set_app_state)
        logForDebugging(f"[spawnInProcessTeammate] Registered {agent_id} in AppState")
        return {
            "success": True,
            "agentId": agent_id,
            "taskId": task_id,
            "abortController": abort_controller,
            "teammateContext": teammate_context,
        }
    except Exception as error:
        error_message = str(error)
        logForDebugging(f"[spawnInProcessTeammate] Failed to spawn {agent_id}: {error_message}")
        return {"success": False, "agentId": agent_id, "error": error_message}


def killInProcessTeammate(taskId, setAppState):
    killed = False
    team_name = None
    agent_id = None
    tool_use_id = None
    description = None

    def _update(prev):
        nonlocal killed, team_name, agent_id, tool_use_id, description
        tasks = _tasks(prev)
        task = tasks.get(taskId)
        if not isinstance(task, dict) or task.get("type") != "in_process_teammate":
            return prev
        if task.get("status") != "running":
            return prev

        identity = task.get("identity") or {}
        team_name = identity.get("teamName")
        agent_id = identity.get("agentId")
        tool_use_id = task.get("toolUseId") or task.get("tool_use_id")
        description = task.get("description")

        abort_controller = task.get("abortController")
        if abort_controller is not None:
            abort_controller.abort()

        unregister_cleanup = task.get("unregisterCleanup")
        if callable(unregister_cleanup):
            unregister_cleanup()

        for callback in task.get("onIdleCallbacks") or []:
            try:
                callback()
            except Exception:
                pass

        killed = True
        updated_team_context = _remove_teammate_from_team_context(prev, agent_id)
        updated_task = {
            **task,
            "status": "killed",
            "notified": True,
            "endTime": time.time() * 1000,
            "onIdleCallbacks": [],
            "messages": [task["messages"][-1]] if task.get("messages") else None,
            "pendingUserMessages": [],
            "inProgressToolUseIDs": None,
            "abortController": None,
            "unregisterCleanup": None,
            "currentWorkAbortController": None,
        }
        next_tasks = dict(tasks)
        next_tasks[taskId] = updated_task

        if isinstance(prev, dict):
            return {**prev, "teamContext": updated_team_context, "tasks": next_tasks}
        prev.teamContext = updated_team_context
        prev.tasks = next_tasks
        return prev

    setAppState(_update)

    if team_name and agent_id:
        removeMemberByAgentId(team_name, agent_id)

    if killed:
        try:
            evictTaskOutput(taskId)
        except Exception:
            pass
        emitTaskTerminatedSdk(taskId, "stopped", {"toolUseId": tool_use_id, "summary": description})

    if agent_id:
        _, _, perfetto_unregister = _get_perfetto_hooks()
        perfetto_unregister(agent_id)

    return killed


def _cfg(value, key):
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _tasks(state):
    if isinstance(state, dict):
        return state.get("tasks", {})
    return getattr(state, "tasks", {})


def _remove_teammate_from_team_context(state, agent_id):
    if isinstance(state, dict):
        team_context = state.get("teamContext")
    else:
        team_context = getattr(state, "teamContext", None)
    if not isinstance(team_context, dict):
        return team_context
    teammates = team_context.get("teammates")
    if not isinstance(teammates, dict) or not agent_id:
        return team_context
    remaining = {key: value for key, value in teammates.items() if key != agent_id}
    return {**team_context, "teammates": remaining}


def _get_perfetto_hooks():
    try:
        from ..telemetry.perfettoTracing import (
            isPerfettoTracingEnabled,
            registerAgent,
            unregisterAgent,
        )

        return isPerfettoTracingEnabled, registerAgent, unregisterAgent
    except Exception:
        return (
            lambda: False,
            lambda agent_id, agent_name, parent_session_id=None: None,
            lambda agent_id: None,
        )


spawn_in_process_teammate = spawnInProcessTeammate
kill_in_process_teammate = killInProcessTeammate