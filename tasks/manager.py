"""TaskManager — central registry for all running and queued tasks.

Mirrors the AppState.tasks map + the task framework utilities from
src/utils/task/framework.ts, stopTask.ts, and related modules.
"""

from __future__ import annotations

import asyncio
import os
import uuid
import logging
from typing import Any, Optional

from .types import (
    TaskBase, ShellTask, AgentTask, TodoTask,
    TaskStatus, TaskType,
)

logger = logging.getLogger(__name__)

_MAX_OUTPUT_BYTES = 2 * 1024 * 1024  # 2 MB per task


class TaskManager:
    """Process-wide singleton that owns every task.

    Mirrors:
      - AppState.tasks dict
      - src/utils/task/framework.ts  (registerTask / updateTaskState)
      - src/tasks/stopTask.ts        (stopTask)
    """

    _instance: Optional["TaskManager"] = None

    @classmethod
    def get(cls) -> "TaskManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._tasks: dict[str, TaskBase] = {}

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _new_id(self) -> str:
        return uuid.uuid4().hex[:12]

    # ── Todo tasks (TaskCreate V2) ──────────────────────────────────────────

    def create_todo(
        self,
        subject: str,
        description: str = "",
        active_form: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> TodoTask:
        """Create a structured todo-style task entry."""
        task = TodoTask(
            id=self._new_id(),
            subject=subject,
            description=description,
            active_form=active_form,
            metadata=metadata or {},
        )
        self._tasks[task.id] = task
        logger.debug("Created todo task %s: %s", task.id, subject)
        return task

    def update_todo(
        self,
        task_id: str,
        *,
        subject: Optional[str] = None,
        description: Optional[str] = None,
        active_form: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        owner: Optional[str] = None,
        add_blocks: Optional[list[str]] = None,
        add_blocked_by: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        delete: bool = False,
    ) -> Optional[TodoTask]:
        """Update a todo task — mirrors TaskUpdateTool."""
        task = self._tasks.get(task_id)
        if task is None or not isinstance(task, TodoTask):
            return None
        if delete:
            del self._tasks[task_id]
            return None
        if subject is not None:
            task.subject = subject
        if description is not None:
            task.description = description
        if active_form is not None:
            task.active_form = active_form
        if status is not None:
            task.status = status
        if owner is not None:
            task.owner = owner
        if add_blocks:
            for t in add_blocks:
                if t not in task.blocks:
                    task.blocks.append(t)
        if add_blocked_by:
            for t in add_blocked_by:
                if t not in task.blocked_by:
                    task.blocked_by.append(t)
        if metadata:
            for k, v in metadata.items():
                if v is None:
                    task.metadata.pop(k, None)
                else:
                    task.metadata[k] = v
        task.touch()
        return task

    # ── Shell tasks (LocalShellTask) ────────────────────────────────────────

    async def spawn_shell(
        self,
        command: str,
        description: str = "",
        cwd: Optional[str] = None,
    ) -> ShellTask:
        """Spawn a background shell command and return immediately."""
        task = ShellTask(
            id=self._new_id(),
            command=command,
            description=description or command[:80],
            status="running",
        )
        self._tasks[task.id] = task
        cwd = cwd or os.getcwd()

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=cwd,
            )
            task._process = proc

            # Collect output in background
            async def _collect() -> None:
                assert proc.stdout is not None
                chunks: list[str] = []
                total = 0
                async for raw in proc.stdout:
                    line = raw.decode("utf-8", errors="replace")
                    chunks.append(line)
                    total += len(line)
                    if total > _MAX_OUTPUT_BYTES:
                        chunks = chunks[-1000:]  # keep tail
                        total = sum(len(c) for c in chunks)
                task.output = "".join(chunks)
                await proc.wait()
                task.exit_code = proc.returncode
                task.status = "completed" if proc.returncode == 0 else "failed"
                task.touch()
                logger.debug("Shell task %s finished rc=%s", task.id, task.exit_code)

            collect_coro = asyncio.create_task(_collect())
            task._output_task = collect_coro
        except Exception as exc:
            task.status = "failed"
            task.output = str(exc)
            task.touch()

        return task

    def stop_shell(self, task_id: str) -> bool:
        """Kill a running shell task — mirrors stopTask.ts."""
        task = self._tasks.get(task_id)
        if not isinstance(task, ShellTask):
            return False
        if task.status != "running":
            return False
        if task._process is not None:
            try:
                task._process.terminate()
            except Exception:
                pass
        task.status = "stopped"
        task.touch()
        return True

    async def get_shell_output(
        self,
        task_id: str,
        block: bool = True,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Return output/status for a shell task — mirrors TaskOutputTool."""
        task = self._tasks.get(task_id)
        if not isinstance(task, ShellTask):
            return {"error": f"No shell task: {task_id}"}

        if block and task.status == "running" and task._output_task is not None:
            try:
                await asyncio.wait_for(asyncio.shield(task._output_task), timeout=timeout)
            except asyncio.TimeoutError:
                return {
                    "retrieval_status": "timeout",
                    "task": task.to_dict() | {"output": task.output[-5000:]},
                }
            except Exception:
                pass

        return {
            "retrieval_status": "success",
            "task": task.to_dict() | {"output": task.output[-10000:]},
        }

    # ── Agent tasks (LocalAgentTask) ────────────────────────────────────────

    def create_agent_task(
        self,
        prompt: str,
        description: str = "",
        agent_name: Optional[str] = None,
    ) -> AgentTask:
        task = AgentTask(
            id=self._new_id(),
            prompt=prompt,
            description=description,
            agent_name=agent_name,
            status="pending",
        )
        self._tasks[task.id] = task
        return task

    # ── Generic getters ─────────────────────────────────────────────────────

    def get_task(self, task_id: str) -> Optional[TaskBase]:
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        task_type: Optional[TaskType] = None,
        status: Optional[TaskStatus] = None,
    ) -> list[TaskBase]:
        tasks = list(self._tasks.values())
        if task_type:
            tasks = [t for t in tasks if t.type == task_type]
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: getattr(t, "start_time", 0))

    def stop_task(self, task_id: str) -> bool:
        """Stop any running task by ID."""
        task = self._tasks.get(task_id)
        if task is None:
            return False
        if isinstance(task, ShellTask):
            return self.stop_shell(task_id)
        if task.status == "running":
            task.status = "stopped"
            task.touch()
            return True
        return False

    async def get_task_output(
        self,
        task_id: str,
        block: bool = True,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Universal output getter for any task type."""
        task = self._tasks.get(task_id)
        if task is None:
            return {"retrieval_status": "not_ready", "task": None,
                    "error": f"No task: {task_id}"}
        if isinstance(task, ShellTask):
            return await self.get_shell_output(task_id, block=block, timeout=timeout)
        # Agent / todo tasks
        return {"retrieval_status": "success", "task": task.to_dict()}
