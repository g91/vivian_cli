"""Port of src/utils/tasks.ts.

This module implements the file-backed task list used by the swarm tools.
"""
from __future__ import annotations

from typing import Any, Dict
import os
from pathlib import Path

from ..bootstrap.state import getIsNonInteractiveSession, getSessionId
from .debug import logError, logForDebugging
from .envUtils import get_vivian_config_home_dir, get_teams_dir, is_env_truthy
from .lockfile import lock
from .slowOperations import jsonParse, jsonStringify
from .teammate import getTeamName
from .teammateContext import getTeammateContext


TaskStatus = str
Task = Dict[str, Any]
ClaimTaskResult = Dict[str, Any]
ClaimTaskOptions = Dict[str, Any]
TeamMember = Dict[str, Any]
AgentStatus = Dict[str, Any]
UnassignTasksResult = Dict[str, Any]


class _Signal:
    def __init__(self) -> None:
        self._listeners: list[Any] = []

    def subscribe(self, callback: Any) -> Any:
        self._listeners.append(callback)

        def _unsubscribe() -> None:
            try:
                self._listeners.remove(callback)
            except ValueError:
                pass

        return _unsubscribe

    def emit(self) -> None:
        for callback in list(self._listeners):
            try:
                callback()
            except Exception:
                pass


tasksUpdated = _Signal()
_leader_team_name: str | None = None
HIGH_WATER_MARK_FILE = ".highwatermark"


onTasksUpdated: Any = tasksUpdated.subscribe  # type: ignore
TASK_STATUSES: tuple[str, ...] = ("pending", "in_progress", "completed")
TaskStatusSchema: Any = TASK_STATUSES  # compatibility shim
TaskSchema: Any = None  # compatibility shim
DEFAULT_TASKS_MODE_TASK_LIST_ID: str = "tasklist"


def _acquire_lock(path: str):
    try:
        return lock(path, timeout_ms=10_000)
    except ImportError:
        logForDebugging(f"[Tasks] filelock unavailable; proceeding without lock for {path}")
        return lambda: None


def setLeaderTeamName(teamName):
    """Sets the leader's team name for task list resolution."""
    global _leader_team_name
    if _leader_team_name == teamName:
        return teamName
    _leader_team_name = str(teamName) if teamName is not None else None
    notifyTasksUpdated()
    return _leader_team_name


def clearLeaderTeamName():
    """Clears the leader's team name."""
    global _leader_team_name
    if _leader_team_name is None:
        return None
    _leader_team_name = None
    notifyTasksUpdated()
    return None


def notifyTasksUpdated():
    """Notify listeners that tasks have been updated."""
    try:
        tasksUpdated.emit()
    except Exception:
        pass
    return None


def getHighWaterMarkPath(taskListId):
    return str(Path(getTasksDir(taskListId)) / HIGH_WATER_MARK_FILE)


async def readHighWaterMark(taskListId):
    path = Path(getHighWaterMarkPath(taskListId))
    try:
        content = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return 0
    except Exception:
        return 0
    try:
        return int(content)
    except ValueError:
        return 0


async def writeHighWaterMark(taskListId, value):
    path = Path(getHighWaterMarkPath(taskListId))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(int(value)), encoding="utf-8")


def isTodoV2Enabled():
    if is_env_truthy(os.environ.get("vivian_CODE_ENABLE_TASKS", "")):
        return True
    return not getIsNonInteractiveSession()


async def resetTaskList(taskListId):
    """Reset a task list and preserve the highest assigned task ID."""
    task_dir = Path(getTasksDir(taskListId))
    task_dir.mkdir(parents=True, exist_ok=True)
    lock_path = await ensureTaskListLockFile(taskListId)
    release = None
    try:
        release = _acquire_lock(lock_path)
        highest = await findHighestTaskIdFromFiles(taskListId)
        if highest > 0:
            existing = await readHighWaterMark(taskListId)
            if highest > existing:
                await writeHighWaterMark(taskListId, highest)
        for child in task_dir.iterdir():
            if child.name.startswith(".") or child.suffix != ".json":
                continue
            try:
                child.unlink()
            except FileNotFoundError:
                pass
        notifyTasksUpdated()
    finally:
        if release is not None:
            release()
    return None


def getTaskListId():
    """Gets the task list ID based on the current context."""
    explicit = os.environ.get("vivian_CODE_TASK_LIST_ID")
    if explicit:
        return explicit
    teammate_ctx = getTeammateContext()
    if teammate_ctx and teammate_ctx.get("teamName"):
        return teammate_ctx["teamName"]
    team_name = getTeamName()
    if team_name:
        return team_name
    return _leader_team_name or getSessionId()


def sanitizePathComponent(input):
    """Sanitizes a string for safe use in file paths."""
    raw = "" if input is None else str(input)
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in raw)


def getTasksDir(taskListId):
    return str(Path(get_vivian_config_home_dir()) / "tasks" / sanitizePathComponent(taskListId))


def getTaskPath(taskListId, taskId):
    return str(Path(getTasksDir(taskListId)) / f"{sanitizePathComponent(taskId)}.json")


async def ensureTasksDir(taskListId):
    Path(getTasksDir(taskListId)).mkdir(parents=True, exist_ok=True)
    return None


async def findHighestTaskIdFromFiles(taskListId):
    """Find the highest numeric task ID from task files."""
    task_dir = Path(getTasksDir(taskListId))
    try:
        files = list(task_dir.iterdir())
    except FileNotFoundError:
        return 0
    highest = 0
    for child in files:
        if child.suffix != ".json":
            continue
        try:
            highest = max(highest, int(child.stem))
        except ValueError:
            continue
    return highest


async def findHighestTaskId(taskListId):
    """Find the highest task ID, considering both files and the high-water mark."""
    from_files = await findHighestTaskIdFromFiles(taskListId)
    from_mark = await readHighWaterMark(taskListId)
    return max(from_files, from_mark)


async def createTask(taskListId, taskData):
    """Create a new task with a unique ID."""
    lock_path = await ensureTaskListLockFile(taskListId)
    release = None
    try:
        release = _acquire_lock(lock_path)
        highest_id = await findHighestTaskId(taskListId)
        task_id = str(highest_id + 1)
        task = {"id": task_id, **dict(taskData or {})}
        normalized = _normalize_task(task)
        Path(getTaskPath(taskListId, task_id)).write_text(
            jsonStringify(normalized, indent=2),
            encoding="utf-8",
        )
        notifyTasksUpdated()
        return task_id
    finally:
        if release is not None:
            release()


async def getTask(taskListId, taskId):
    path = Path(getTaskPath(taskListId, taskId))
    try:
        data = jsonParse(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except Exception as error:
        logForDebugging(f"[Tasks] Failed to read task {taskId}: {error}")
        logError(f"Failed to read task {taskId}", error if isinstance(error, Exception) else None)
        return None

    if not isinstance(data, dict):
        logForDebugging(f"[Tasks] Task {taskId} had non-object JSON payload")
        return None

    if os.environ.get("USER_TYPE") == "ant":
        status = data.get("status")
        if status == "open":
            data["status"] = "pending"
        elif status == "resolved":
            data["status"] = "completed"
        elif status in {"planning", "implementing", "reviewing", "verifying"}:
            data["status"] = "in_progress"

    normalized = _normalize_task(data)
    if not normalized.get("id"):
        return None
    return normalized


async def updateTaskUnsafe(taskListId, taskId, updates):
    existing = await getTask(taskListId, taskId)
    if not existing:
        return None
    updated = _normalize_task({**existing, **dict(updates or {}), "id": str(taskId)})
    Path(getTaskPath(taskListId, taskId)).write_text(
        jsonStringify(updated, indent=2),
        encoding="utf-8",
    )
    notifyTasksUpdated()
    return updated


async def updateTask(taskListId, taskId, updates):
    existing = await getTask(taskListId, taskId)
    if not existing:
        return None
    task_path = getTaskPath(taskListId, taskId)
    release = None
    try:
        release = _acquire_lock(task_path)
        return await updateTaskUnsafe(taskListId, taskId, updates)
    finally:
        if release is not None:
            release()


async def deleteTask(taskListId, taskId):
    path = Path(getTaskPath(taskListId, taskId))
    try:
        numeric_id = int(str(taskId))
    except ValueError:
        numeric_id = None

    try:
        if numeric_id is not None:
            current_mark = await readHighWaterMark(taskListId)
            if numeric_id > current_mark:
                await writeHighWaterMark(taskListId, numeric_id)
        path.unlink()
    except FileNotFoundError:
        return False
    except Exception:
        return False

    all_tasks = await listTasks(taskListId)
    for task in all_tasks:
        new_blocks = [item for item in task.get("blocks", []) if item != str(taskId)]
        new_blocked_by = [item for item in task.get("blockedBy", []) if item != str(taskId)]
        if new_blocks != task.get("blocks", []) or new_blocked_by != task.get("blockedBy", []):
            await updateTask(taskListId, task["id"], {"blocks": new_blocks, "blockedBy": new_blocked_by})

    notifyTasksUpdated()
    return True


async def listTasks(taskListId):
    task_dir = Path(getTasksDir(taskListId))
    try:
        files = sorted(task_dir.iterdir(), key=lambda child: child.name)
    except FileNotFoundError:
        return []

    task_ids = [child.stem for child in files if child.suffix == ".json" and not child.name.startswith(".")]
    results = await _gather_tasks(taskListId, task_ids)
    return [task for task in results if task is not None]


async def blockTask(taskListId, fromTaskId, toTaskId):
    from_task, to_task = await getTask(taskListId, fromTaskId), await getTask(taskListId, toTaskId)
    if not from_task or not to_task:
        return False

    if str(toTaskId) not in from_task.get("blocks", []):
        await updateTask(taskListId, fromTaskId, {"blocks": [*from_task.get("blocks", []), str(toTaskId)]})
    if str(fromTaskId) not in to_task.get("blockedBy", []):
        await updateTask(taskListId, toTaskId, {"blockedBy": [*to_task.get("blockedBy", []), str(fromTaskId)]})
    return True


def getTaskListLockPath(taskListId):
    """Gets the lock file path for a task list."""
    return str(Path(getTasksDir(taskListId)) / ".lock")


async def ensureTaskListLockFile(taskListId):
    """Ensures the lock file exists for a task list."""
    await ensureTasksDir(taskListId)
    lock_path = Path(getTaskListLockPath(taskListId))
    try:
        lock_path.touch(exist_ok=True)
    except Exception:
        pass
    return str(lock_path)


async def claimTask(taskListId, taskId, claimantAgentId, options={}):
    """Attempt to claim a task for an agent."""
    task_before_lock = await getTask(taskListId, taskId)
    if not task_before_lock:
        return {"success": False, "reason": "task_not_found"}

    if (options or {}).get("checkAgentBusy"):
        return await claimTaskWithBusyCheck(taskListId, taskId, claimantAgentId)

    task_path = getTaskPath(taskListId, taskId)
    release = None
    try:
        release = _acquire_lock(task_path)
        task = await getTask(taskListId, taskId)
        if not task:
            return {"success": False, "reason": "task_not_found"}
        if task.get("owner") and task.get("owner") != claimantAgentId:
            return {"success": False, "reason": "already_claimed", "task": task}
        if task.get("status") == "completed":
            return {"success": False, "reason": "already_resolved", "task": task}

        all_tasks = await listTasks(taskListId)
        unresolved_ids = {item.get("id") for item in all_tasks if item.get("status") != "completed"}
        blocked_by_tasks = [item for item in task.get("blockedBy", []) if item in unresolved_ids]
        if blocked_by_tasks:
            return {
                "success": False,
                "reason": "blocked",
                "task": task,
                "blockedByTasks": blocked_by_tasks,
            }

        updated = await updateTaskUnsafe(taskListId, taskId, {"owner": claimantAgentId})
        return {"success": True, "task": updated}
    except Exception as error:
        logForDebugging(f"[Tasks] Failed to claim task {taskId}: {error}")
        logError(f"Failed to claim task {taskId}", error if isinstance(error, Exception) else None)
        return {"success": False, "reason": "task_not_found"}
    finally:
        if release is not None:
            release()


async def claimTaskWithBusyCheck(taskListId, taskId, claimantAgentId):
    """Claim a task with an atomic busy check."""
    lock_path = await ensureTaskListLockFile(taskListId)
    release = None
    try:
        release = _acquire_lock(lock_path)
        all_tasks = await listTasks(taskListId)
        task = next((item for item in all_tasks if item.get("id") == str(taskId)), None)
        if not task:
            return {"success": False, "reason": "task_not_found"}
        if task.get("owner") and task.get("owner") != claimantAgentId:
            return {"success": False, "reason": "already_claimed", "task": task}
        if task.get("status") == "completed":
            return {"success": False, "reason": "already_resolved", "task": task}

        unresolved_ids = {item.get("id") for item in all_tasks if item.get("status") != "completed"}
        blocked_by_tasks = [item for item in task.get("blockedBy", []) if item in unresolved_ids]
        if blocked_by_tasks:
            return {
                "success": False,
                "reason": "blocked",
                "task": task,
                "blockedByTasks": blocked_by_tasks,
            }

        agent_open_tasks = [
            item for item in all_tasks
            if item.get("status") != "completed" and item.get("owner") == claimantAgentId and item.get("id") != str(taskId)
        ]
        if agent_open_tasks:
            return {
                "success": False,
                "reason": "agent_busy",
                "task": task,
                "busyWithTasks": [item.get("id") for item in agent_open_tasks],
            }

        updated = await updateTask(taskListId, taskId, {"owner": claimantAgentId})
        return {"success": True, "task": updated}
    except Exception as error:
        logForDebugging(f"[Tasks] Failed to claim task {taskId} with busy check: {error}")
        logError(f"Failed to claim task {taskId} with busy check", error if isinstance(error, Exception) else None)
        return {"success": False, "reason": "task_not_found"}
    finally:
        if release is not None:
            release()


def sanitizeName(name):
    """Sanitize a team name for path usage."""
    raw = "" if name is None else str(name)
    return "".join(ch if ch.isalnum() else "-" for ch in raw).lower()


async def readTeamMembers(teamName):
    """Read team member info from the team's config.json file."""
    team_file_path = Path(get_teams_dir()) / sanitizeName(teamName) / "config.json"
    try:
        team_file = jsonParse(team_file_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except Exception as error:
        logForDebugging(f"[Tasks] Failed to read team file for {teamName}: {error}")
        return None
    if not isinstance(team_file, dict):
        return None
    members = []
    for member in team_file.get("members", []) or []:
        if not isinstance(member, dict):
            continue
        members.append(
            {
                "agentId": member.get("agentId"),
                "name": member.get("name"),
                "agentType": member.get("agentType"),
            }
        )
    return {
        "leadAgentId": team_file.get("leadAgentId"),
        "members": members,
    }


async def getAgentStatuses(teamName):
    """Get current agent busy/idle status from task ownership."""
    team_data = await readTeamMembers(teamName)
    if not team_data:
        return None

    task_list_id = sanitizeName(teamName)
    all_tasks = await listTasks(task_list_id)
    unresolved_by_owner: dict[str, list[str]] = {}
    for task in all_tasks:
        if task.get("status") == "completed" or not task.get("owner"):
            continue
        unresolved_by_owner.setdefault(task["owner"], []).append(task["id"])

    statuses = []
    for member in team_data.get("members", []):
        tasks_by_name = unresolved_by_owner.get(member.get("name") or "", [])
        tasks_by_id = unresolved_by_owner.get(member.get("agentId") or "", [])
        current_tasks = _uniq([*tasks_by_name, *tasks_by_id])
        statuses.append(
            {
                "agentId": member.get("agentId"),
                "name": member.get("name"),
                "agentType": member.get("agentType"),
                "status": "idle" if not current_tasks else "busy",
                "currentTasks": current_tasks,
            }
        )
    return statuses


async def unassignTeammateTasks(teamName, teammateId, teammateName, reason):
    """Unassign unresolved tasks from a departing teammate."""
    tasks = await listTasks(teamName)
    unresolved_assigned_tasks = [
        task for task in tasks
        if task.get("status") != "completed"
        and task.get("owner") in {teammateId, teammateName}
    ]

    for task in unresolved_assigned_tasks:
        await updateTask(teamName, task["id"], {"owner": None, "status": "pending"})

    if unresolved_assigned_tasks:
        logForDebugging(
            f"[Tasks] Unassigned {len(unresolved_assigned_tasks)} task(s) from {teammateName}"
        )

    action_verb = "was terminated" if reason == "terminated" else "has shut down"
    notification_message = f"{teammateName} {action_verb}."
    if unresolved_assigned_tasks:
        task_list = ", ".join(
            f'#{task.get("id")} "{task.get("subject", "")}"' for task in unresolved_assigned_tasks
        )
        notification_message += (
            f" {len(unresolved_assigned_tasks)} task(s) were unassigned: {task_list}. "
            "Use TaskList to check availability and TaskUpdate with owner to reassign them to idle teammates."
        )

    return {
        "unassignedTasks": [
            {"id": task.get("id"), "subject": task.get("subject")} for task in unresolved_assigned_tasks
        ],
        "notificationMessage": notification_message,
    }


async def _gather_tasks(taskListId: str, task_ids: list[str]) -> list[Task | None]:
    return [await getTask(taskListId, task_id) for task_id in task_ids]


def _normalize_task(task: Dict[str, Any]) -> Task:
    normalized = dict(task)
    normalized["id"] = str(normalized.get("id", ""))
    normalized["subject"] = str(normalized.get("subject", normalized.get("title", "")) or "")
    normalized["description"] = str(normalized.get("description", normalized.get("content", "")) or "")
    active_form = normalized.get("activeForm")
    if active_form is not None:
        normalized["activeForm"] = str(active_form)
    owner = normalized.get("owner")
    if owner is not None and owner != "":
        normalized["owner"] = str(owner)
    else:
        normalized.pop("owner", None)
    status = str(normalized.get("status", "pending") or "pending")
    if status not in TASK_STATUSES:
        status = "pending"
    normalized["status"] = status
    normalized["blocks"] = [str(item) for item in list(normalized.get("blocks") or [])]
    normalized["blockedBy"] = [str(item) for item in list(normalized.get("blockedBy") or normalized.get("blocked_by") or [])]
    metadata = normalized.get("metadata")
    normalized["metadata"] = metadata if isinstance(metadata, dict) else {}
    normalized.pop("blocked_by", None)
    return normalized


def _uniq(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


set_leader_team_name = setLeaderTeamName
clear_leader_team_name = clearLeaderTeamName
notify_tasks_updated = notifyTasksUpdated
get_high_water_mark_path = getHighWaterMarkPath
read_high_water_mark = readHighWaterMark
write_high_water_mark = writeHighWaterMark
is_todo_v2_enabled = isTodoV2Enabled
reset_task_list = resetTaskList
get_task_list_id = getTaskListId
sanitize_path_component = sanitizePathComponent
get_tasks_dir = getTasksDir
get_task_path = getTaskPath
ensure_tasks_dir = ensureTasksDir
find_highest_task_id_from_files = findHighestTaskIdFromFiles
find_highest_task_id = findHighestTaskId
create_task = createTask
get_task = getTask
update_task_unsafe = updateTaskUnsafe
update_task = updateTask
delete_task = deleteTask
list_tasks = listTasks
block_task = blockTask
get_task_list_lock_path = getTaskListLockPath
ensure_task_list_lock_file = ensureTaskListLockFile
claim_task = claimTask
claim_task_with_busy_check = claimTaskWithBusyCheck
sanitize_name = sanitizeName
read_team_members = readTeamMembers
get_agent_statuses = getAgentStatuses
unassign_teammate_tasks = unassignTeammateTasks