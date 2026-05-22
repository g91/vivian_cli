"""Local agent task helpers mirroring src/tasks/LocalAgentTask/LocalAgentTask.tsx."""

from __future__ import annotations

import time
from dataclasses import is_dataclass, replace
from typing import Any, Callable, Optional

from ...Task import createTaskStateBase
from ...utils.abortController import create_abort_controller, create_child_abort_controller
from ...utils.cleanupRegistry import register_cleanup
from ...utils.task.framework import PANEL_GRACE_MS, registerTask, updateTaskState
from ..types import AgentProgress, LocalAgentTaskState


def _task_replace(task: Any, **updates: Any) -> Any:
    if isinstance(task, dict):
        merged = dict(task)
        merged.update(updates)
        return merged
    if is_dataclass(task):
        return replace(task, **updates)
    for key, value in updates.items():
        setattr(task, key, value)
    return task


def isLocalAgentTask(task: Any) -> bool:
    return (task.get("type") if isinstance(task, dict) else getattr(task, "type", None)) == "local_agent"


def isPanelAgentTask(task: Any) -> bool:
    return isLocalAgentTask(task) and (task.get("agent_type") if isinstance(task, dict) else getattr(task, "agent_type", None)) != "main-session"


def queuePendingMessage(taskId: str, msg: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    updateTaskState(taskId, setAppState, lambda task: _task_replace(task, pending_messages=[*getattr(task, "pending_messages", []), msg]))


def appendMessageToLocalAgent(taskId: str, message: Any, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    def _append(task: Any) -> Any:
        existing = getattr(task, "messages", None) or []
        return _task_replace(task, messages=[*existing, message])

    updateTaskState(taskId, setAppState, _append)


def drainPendingMessages(taskId: str, getAppState: Callable[[], Any], setAppState: Callable[[Callable[[Any], Any]], None]) -> list[str]:
    state = getAppState()
    tasks = state.get("tasks", {}) if isinstance(state, dict) else getattr(state, "tasks", {})
    task = tasks.get(taskId)
    if not isLocalAgentTask(task):
        return []
    drained = list(getattr(task, "pending_messages", []))
    if not drained:
        return []
    updateTaskState(taskId, setAppState, lambda current: _task_replace(current, pending_messages=[]))
    return drained


def markAgentsNotified(taskId: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    updateTaskState(taskId, setAppState, lambda task: task if getattr(task, "notified", False) else _task_replace(task, notified=True))


def updateAgentProgress(taskId: str, progress: AgentProgress, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    def _update(task: Any) -> Any:
        if getattr(task, "status", None) != "running":
            return task
        existing = getattr(task, "progress", None)
        if existing is not None and getattr(existing, "summary", None):
            progress.summary = existing.summary
        return _task_replace(task, progress=progress)

    updateTaskState(taskId, setAppState, _update)


def updateAgentSummary(taskId: str, summary: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    def _update(task: Any) -> Any:
        if getattr(task, "status", None) != "running":
            return task
        progress = getattr(task, "progress", None) or AgentProgress()
        progress.summary = summary
        return _task_replace(task, progress=progress)

    updateTaskState(taskId, setAppState, _update)


def killAsyncAgent(taskId: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    def _kill(task: Any) -> Any:
        if getattr(task, "status", None) != "running":
            return task
        abort_controller = getattr(task, "abort_controller", None)
        if abort_controller is not None:
            abort_controller.abort()
        cleanup = getattr(task, "unregister_cleanup", None)
        if callable(cleanup):
            cleanup()
        evict_after = None if getattr(task, "retain", False) else time.time() * 1000 + PANEL_GRACE_MS
        return _task_replace(task, status="killed", end_time=time.time() * 1000, evict_after=evict_after, abort_controller=None, unregister_cleanup=None, selected_agent=None)

    updateTaskState(taskId, setAppState, _kill)


def killAllRunningAgentTasks(tasks: dict[str, Any], setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    for task_id, task in tasks.items():
        if isLocalAgentTask(task) and getattr(task, "status", None) == "running":
            killAsyncAgent(task_id, setAppState)


def completeAgentTask(result: Any, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    task_id = getattr(result, "agentId", None) or result.get("agentId")
    if task_id is None:
        return

    def _complete(task: Any) -> Any:
        if getattr(task, "status", None) != "running":
            return task
        cleanup = getattr(task, "unregister_cleanup", None)
        if callable(cleanup):
            cleanup()
        evict_after = None if getattr(task, "retain", False) else time.time() * 1000 + PANEL_GRACE_MS
        return _task_replace(task, status="completed", result=result, end_time=time.time() * 1000, evict_after=evict_after, abort_controller=None, unregister_cleanup=None, selected_agent=None)

    updateTaskState(task_id, setAppState, _complete)


def failAgentTask(taskId: str, error: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    def _fail(task: Any) -> Any:
        if getattr(task, "status", None) != "running":
            return task
        cleanup = getattr(task, "unregister_cleanup", None)
        if callable(cleanup):
            cleanup()
        evict_after = None if getattr(task, "retain", False) else time.time() * 1000 + PANEL_GRACE_MS
        return _task_replace(task, status="failed", error=error, end_time=time.time() * 1000, evict_after=evict_after, abort_controller=None, unregister_cleanup=None, selected_agent=None)

    updateTaskState(taskId, setAppState, _fail)


async def _cleanup_agent(agent_id: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    killAsyncAgent(agent_id, setAppState)


def registerAsyncAgent(*, agentId: str, description: str, prompt: str, selectedAgent: dict[str, Any], setAppState: Callable[[Callable[[Any], Any]], None], parentAbortController: Optional[Any] = None, toolUseId: Optional[str] = None) -> LocalAgentTaskState:
    abort_controller = create_child_abort_controller(parentAbortController) if parentAbortController else create_abort_controller()
    task_state = createTaskStateBase(
        agentId,
        "local_agent",
        description,
        toolUseId,
        cls=LocalAgentTaskState,
        status="running",
        agent_id=agentId,
        prompt=prompt,
        selected_agent=selectedAgent,
        agent_type=selectedAgent.get("agentType", "general-purpose"),
        abort_controller=abort_controller,
        retrieved=False,
        last_reported_tool_count=0,
        last_reported_token_count=0,
        is_backgrounded=True,
        pending_messages=[],
        retain=False,
        disk_loaded=False,
    )
    unregister = register_cleanup(lambda: _cleanup_agent(agentId, setAppState))
    task_state.unregister_cleanup = unregister
    registerTask(task_state, setAppState)
    return task_state


def registerAgentForeground(*, agentId: str, description: str, prompt: str, selectedAgent: dict[str, Any], setAppState: Callable[[Callable[[Any], Any]], None], autoBackgroundMs: Optional[int] = None, toolUseId: Optional[str] = None) -> dict[str, Any]:
    task_state = registerAsyncAgent(
        agentId=agentId,
        description=description,
        prompt=prompt,
        selectedAgent=selectedAgent,
        setAppState=setAppState,
        toolUseId=toolUseId,
    )
    updateTaskState(agentId, setAppState, lambda task: _task_replace(task, is_backgrounded=False))
    return {"taskId": agentId, "backgroundSignal": None, "cancelAutoBackground": None if not autoBackgroundMs else (lambda: None)}


def backgroundAgentTask(taskId: str, getAppState: Callable[[], Any], setAppState: Callable[[Callable[[Any], Any]], None]) -> bool:
    state = getAppState()
    tasks = state.get("tasks", {}) if isinstance(state, dict) else getattr(state, "tasks", {})
    task = tasks.get(taskId)
    if not isLocalAgentTask(task) or getattr(task, "is_backgrounded", False):
        return False
    updateTaskState(taskId, setAppState, lambda current: _task_replace(current, is_backgrounded=True))
    return True


def unregisterAgentForeground(taskId: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
    def _remove(prev: Any) -> Any:
        prev_tasks = prev.get("tasks", {}) if isinstance(prev, dict) else getattr(prev, "tasks", {})
        task = prev_tasks.get(taskId)
        if not isLocalAgentTask(task) or getattr(task, "is_backgrounded", False):
            return prev
        cleanup = getattr(task, "unregister_cleanup", None)
        if callable(cleanup):
            cleanup()
        next_tasks = dict(prev_tasks)
        next_tasks.pop(taskId, None)
        if isinstance(prev, dict):
            next_state = dict(prev)
            next_state["tasks"] = next_tasks
            return next_state
        setattr(prev, "tasks", next_tasks)
        return prev

    setAppState(_remove)


class _LocalAgentTaskImpl:
    name = "LocalAgentTask"
    type = "local_agent"

    async def kill(self, taskId: str, setAppState: Callable[[Callable[[Any], Any]], None]) -> None:
        killAsyncAgent(taskId, setAppState)


LocalAgentTask = _LocalAgentTaskImpl()