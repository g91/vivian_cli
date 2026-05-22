"""In-process teammate runner."""
from __future__ import annotations

import asyncio
import html
import json
import time
from contextvars import ContextVar
from typing import Any, Callable, Dict, Optional

from ...tasks.InProcessTeammateTask.InProcessTeammateTask import appendTeammateMessage
from ...tasks.InProcessTeammateTask.types import appendCappedMessage
from ...tools.AgentTool.runAgent import runAgent
from ..abortController import create_abort_controller
from ..task.framework import updateTaskState as _update_task_state
from ..teammateContext import runWithTeammateContext
from ..teammateMailbox import (
    TEAMMATE_MESSAGE_TAG,
    createIdleNotification,
    isShutdownRequest,
    markMessageAsReadByIndex,
    readMailbox,
    writeToMailbox,
)
from .constants import TEAM_LEAD_NAME


SetAppStateFn = Any
InProcessRunnerConfig = Dict[str, Any]
InProcessRunnerResult = Dict[str, Any]
WaitResult = Any

_set_app_state_var: ContextVar[Any] = ContextVar("in_process_runner_set_app_state", default=None)
_get_app_state_var: ContextVar[Any] = ContextVar("in_process_runner_get_app_state", default=None)


def createInProcessCanUseTool(identity, abortController, onPermissionWaitMs=None):
    """Create a permissive canUseTool callback for in-process teammates."""

    async def _can_use_tool(tool, input_data, *_args, forceDecision=None, **_kwargs):
        if forceDecision is not None:
            return forceDecision
        if abortController is not None and getattr(abortController, "signal", None) is not None:
            if abortController.signal.aborted:
                return {"behavior": "ask", "message": "Aborted"}
        if callable(onPermissionWaitMs):
            onPermissionWaitMs(0)
        _ = identity
        _ = tool
        return {
            "behavior": "allow",
            "updatedInput": input_data if isinstance(input_data, dict) else {},
        }

    return _can_use_tool


def formatAsTeammateMessage(from_, content, color=None, summary=None):
    """Format a leader-facing teammate message using the structured XML wrapper."""
    attrs = [f'teammate_id="{html.escape(str(from_ or ""), quote=True)}"']
    if color:
        attrs.append(f'color="{html.escape(str(color), quote=True)}"')
    if summary:
        attrs.append(f'summary="{html.escape(str(summary), quote=True)}"')
    body = html.escape(str(content or ""))
    return f"<{TEAMMATE_MESSAGE_TAG} {' '.join(attrs)}>\n{body}\n</{TEAMMATE_MESSAGE_TAG}>"


def updateTaskState(taskId, updater=None):
    """Update task state using the AppState setter captured for this runner."""
    set_app_state = _set_app_state_var.get()
    if set_app_state is None or updater is None:
        return None
    _update_task_state(taskId, set_app_state, updater)
    return None


async def sendMessageToLeader(from_, text, color, teamName):
    """Send a teammate message to the leader mailbox."""
    message = {
        "from": from_,
        "text": text,
        "timestamp": _now_iso(),
        "color": color,
    }
    await writeToMailbox(TEAM_LEAD_NAME, message, teamName)
    return message


async def sendIdleNotification(agentName, agentColor, teamName, options=None):
    """Send an idle notification to the leader mailbox."""
    payload = createIdleNotification(agentName, options or {})
    await writeToMailbox(
        TEAM_LEAD_NAME,
        {
            "from": agentName,
            "text": json.dumps(payload),
            "timestamp": _now_iso(),
            "color": agentColor,
            "summary": (options or {}).get("summary"),
        },
        teamName,
    )
    return payload


def findAvailableTask(tasks):
    """Find the first unclaimed task from a task list snapshot."""
    for task in tasks or []:
        if not isinstance(task, dict):
            continue
        status = task.get("status")
        assignee = (
            task.get("owner")
            or task.get("assignee")
            or task.get("assigneeAgentId")
            or task.get("claimantAgentId")
        )
        if assignee:
            continue
        if status in {None, "pending", "todo", "open"}:
            return task
    return None


def formatTaskAsPrompt(task):
    """Format a claimed task as a prompt for the teammate."""
    if not isinstance(task, dict):
        return str(task)
    title = task.get("title") or task.get("name") or "Task"
    description = task.get("description") or task.get("content") or ""
    task_id = task.get("id")
    parts = [title.strip()]
    if description:
        parts.append(str(description).strip())
    if task_id:
        parts.append(f"Task ID: {task_id}")
    return "\n\n".join(part for part in parts if part)


async def tryClaimNextTask(taskListId, agentName):
    """Best-effort task claim using the shared task-list helpers when available."""
    if not taskListId:
        return None
    try:
        from ..tasks import claimTask, listTasks
    except Exception:
        return None

    tasks = await listTasks(taskListId)
    if not isinstance(tasks, list):
        return None
    available = findAvailableTask(tasks)
    if not available:
        return None

    task_id = available.get("id")
    if not task_id:
        return None

    try:
        claim_result = await claimTask(taskListId, task_id, agentName)
    except Exception:
        return None
    if claim_result is False:
        return None
    return available


async def waitForNextPromptOrShutdown(identity, abortController, taskId, getAppState=None):
    """Wait for the next prompt from AppState or mailbox, or a shutdown signal."""
    while True:
        if _is_aborted(abortController):
            return {"type": "shutdown", "reason": "aborted"}

        task = _get_task_snapshot(taskId, getAppState)
        if task is not None:
            if _task_field(task, "shutdownRequested", "shutdown_requested", default=False):
                return {"type": "shutdown", "reason": "requested"}

            pending_messages = list(_task_field(task, "pendingUserMessages", "pending_user_messages", default=[]) or [])
            if pending_messages:
                next_prompt = pending_messages[0]
                updateTaskState(taskId, lambda current: _with_task_updates(current, pendingUserMessages=pending_messages[1:], pending_user_messages=pending_messages[1:]))
                return {"type": "prompt", "prompt": next_prompt, "source": "app_state"}

        agent_name = _field(identity, "agentName", "agent_name")
        team_name = _field(identity, "teamName", "team_name")
        if agent_name and team_name:
            mailbox = await readMailbox(agent_name, team_name)
            for index, message in enumerate(mailbox):
                if message.get("read"):
                    continue
                await markMessageAsReadByIndex(agent_name, team_name, index)
                text = str(message.get("text") or "")
                if isShutdownRequest(text):
                    return {"type": "shutdown", "reason": "mailbox"}
                if text:
                    return {"type": "prompt", "prompt": text, "source": "mailbox", "message": message}

        await asyncio.sleep(0.25)


async def runInProcessTeammate(config):
    """Run an in-process teammate until shutdown or abort."""
    set_app_state = _cfg(config, "setAppState")
    get_app_state = _cfg(config, "getAppState")
    teammate_context = _cfg(config, "teammateContext")
    identity = _cfg(config, "identity") or teammate_context or {}
    task_id = _cfg(config, "taskId")
    abort_controller = _cfg(config, "abortController") or _field(teammate_context, "abortController", "abort_controller")
    agent_definition = _cfg(config, "selectedAgent") or _cfg(config, "agentDefinition") or {"agentType": "general-purpose"}
    initial_prompt = _cfg(config, "prompt")

    async def _runner() -> InProcessRunnerResult:
        if initial_prompt:
            updateTaskState(task_id, lambda task: _with_task_updates(task, isIdle=False, is_idle=False))

        pending_prompts: list[str] = [str(initial_prompt)] if initial_prompt else []
        last_output: Optional[str] = None

        while True:
            if _is_aborted(abort_controller):
                break

            if not pending_prompts:
                wait_result = await waitForNextPromptOrShutdown(identity, abort_controller, task_id, get_app_state)
                if wait_result.get("type") == "shutdown":
                    break
                prompt = str(wait_result.get("prompt") or "").strip()
                if prompt:
                    pending_prompts.append(prompt)
                else:
                    continue

            prompt = pending_prompts.pop(0).strip()
            if not prompt:
                continue

            current_work_abort_controller = create_abort_controller()
            updateTaskState(
                task_id,
                lambda task: _with_task_updates(
                    task,
                    status="running",
                    isIdle=False,
                    is_idle=False,
                    error=None,
                    currentWorkAbortController=current_work_abort_controller,
                    current_work_abort_controller=current_work_abort_controller,
                    messages=appendCappedMessage(
                        _task_field(task, "messages", default=[]),
                        {"role": "user", "content": prompt},
                    ),
                ),
            )

            try:
                output = await runAgent(agent_definition, prompt)
                last_output = output
                summary = _summary_from_text(output)
                formatted_message = formatAsTeammateMessage(
                    _field(identity, "agentName", "agent_name") or _field(identity, "agentId", "agent_id") or "teammate",
                    output,
                    color=_field(identity, "color"),
                    summary=summary,
                )

                if set_app_state is not None:
                    appendTeammateMessage(task_id, {"role": "assistant", "content": output}, set_app_state)

                await sendMessageToLeader(
                    _field(identity, "agentName", "agent_name") or _field(identity, "agentId", "agent_id") or "teammate",
                    formatted_message,
                    _field(identity, "color"),
                    _field(identity, "teamName", "team_name"),
                )
                await sendIdleNotification(
                    _field(identity, "agentName", "agent_name") or _field(identity, "agentId", "agent_id") or "teammate",
                    _field(identity, "color"),
                    _field(identity, "teamName", "team_name"),
                    {"summary": summary, "completedStatus": "completed"},
                )

                updateTaskState(
                    task_id,
                    lambda task: _with_task_updates(
                        task,
                        result=output,
                        error=None,
                        isIdle=True,
                        is_idle=True,
                        currentWorkAbortController=None,
                        current_work_abort_controller=None,
                    ),
                )
            except Exception as error:
                message = str(error)
                last_output = message
                updateTaskState(
                    task_id,
                    lambda task: _with_task_updates(
                        task,
                        error=message,
                        isIdle=True,
                        is_idle=True,
                        currentWorkAbortController=None,
                        current_work_abort_controller=None,
                    ),
                )
                await sendIdleNotification(
                    _field(identity, "agentName", "agent_name") or _field(identity, "agentId", "agent_id") or "teammate",
                    _field(identity, "color"),
                    _field(identity, "teamName", "team_name"),
                    {
                        "summary": _summary_from_text(message),
                        "completedStatus": "failed",
                        "failureReason": message,
                    },
                )

        if task_id:
            updateTaskState(
                task_id,
                lambda task: task
                if _task_field(task, "status", default="running") != "running"
                else _with_task_updates(
                    task,
                    status="completed",
                    endTime=time.time() * 1000,
                    end_time=time.time() * 1000,
                    isIdle=True,
                    is_idle=True,
                    currentWorkAbortController=None,
                    current_work_abort_controller=None,
                ),
            )

        return {"success": True, "status": "completed", "result": last_output}

    token_set = _set_app_state_var.set(set_app_state)
    token_get = _get_app_state_var.set(get_app_state)
    try:
        if teammate_context:
            coroutine = runWithTeammateContext(teammate_context, _runner)
            return await coroutine
        return await _runner()
    finally:
        _set_app_state_var.reset(token_set)
        _get_app_state_var.reset(token_get)


def startInProcessTeammate(config):
    """Start an in-process teammate in the background."""
    return asyncio.create_task(runInProcessTeammate(config))


def _cfg(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _field(value: Any, *names: str) -> Any:
    if isinstance(value, dict):
        for name in names:
            if name in value:
                return value[name]
        return None
    for name in names:
        if hasattr(value, name):
            return getattr(value, name)
    return None


def _task_field(task: Any, *names: str, default: Any = None) -> Any:
    value = _field(task, *names)
    return default if value is None else value


def _with_task_updates(task: Any, **updates: Any) -> Any:
    if isinstance(task, dict):
        merged = dict(task)
        merged.update(updates)
        return merged
    try:
        from copy import copy

        cloned = copy(task)
        for key, value in updates.items():
            setattr(cloned, key, value)
        return cloned
    except Exception:
        return task


def _get_task_snapshot(task_id: Any, get_app_state: Any) -> Any:
    if not task_id or get_app_state is None:
        return None
    state = get_app_state() if callable(get_app_state) else get_app_state
    if state is None:
        return None
    tasks = state.get("tasks", {}) if isinstance(state, dict) else getattr(state, "tasks", {})
    if not isinstance(tasks, dict):
        return None
    return tasks.get(task_id)


def _is_aborted(abort_controller: Any) -> bool:
    signal = getattr(abort_controller, "signal", None)
    return bool(signal is not None and getattr(signal, "aborted", False))


def _summary_from_text(text: Optional[str], limit: int = 140) -> Optional[str]:
    if not text:
        return None
    trimmed = " ".join(str(text).split())
    if len(trimmed) <= limit:
        return trimmed
    return trimmed[: limit - 3] + "..."


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")