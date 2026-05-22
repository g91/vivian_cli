"""Task types — mirrors src/tasks/types.ts and LocalShellTask/guards.ts."""

from __future__ import annotations

import asyncio
import time
from dataclasses import fields, dataclass, field
from typing import Any, Literal, Optional


TaskStatus = Literal[
    "pending",
    "running",
    "completed",
    "failed",
    "killed",
    "stopped",
    "in_progress",
]

TaskType = Literal[
    "local_bash",
    "local_agent",
    "remote_agent",
    "in_process_teammate",
    "local_workflow",
    "monitor_mcp",
    "dream",
    "todo",
]

BashTaskKind = Literal["bash", "monitor"]
RemoteTaskType = Literal[
    "remote-agent",
    "ultraplan",
    "ultrareview",
    "autofix-pr",
    "background-pr",
]


@dataclass
class TaskStateBase:
    id: str
    type: TaskType
    description: str
    status: TaskStatus = "pending"
    tool_use_id: Optional[str] = None
    start_time: float = field(default_factory=lambda: time.time() * 1000)
    end_time: Optional[float] = None
    total_paused_ms: int = 0
    output_file: str = ""
    output_offset: int = 0
    notified: bool = False

    def touch(self) -> None:
        if self.status in {"completed", "failed", "killed", "stopped"} and self.end_time is None:
            self.end_time = time.time() * 1000

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for dataclass_field in fields(self):
            if dataclass_field.name.startswith("_"):
                continue
            data[dataclass_field.name] = getattr(self, dataclass_field.name)
        return data


@dataclass
class LocalShellTaskState(TaskStateBase):
    type: TaskType = field(default="local_bash", init=False)
    command: str = ""
    result: Optional[dict[str, Any]] = None
    completion_status_sent_in_attachment: bool = False
    shell_command: Any = None
    unregister_cleanup: Optional[Any] = None
    cleanup_timeout_id: Optional[Any] = None
    last_reported_total_lines: int = 0
    is_backgrounded: bool = True
    agent_id: Optional[str] = None
    kind: Optional[BashTaskKind] = None
    output: str = ""
    exit_code: Optional[int] = None
    evict_after: Optional[float] = None
    _process: Optional[asyncio.subprocess.Process] = field(default=None, repr=False, compare=False)
    _output_task: Optional[asyncio.Task[Any]] = field(default=None, repr=False, compare=False)


@dataclass
class ToolActivity:
    tool_name: str
    input: dict[str, Any]
    activity_description: Optional[str] = None
    is_search: Optional[bool] = None
    is_read: Optional[bool] = None


@dataclass
class AgentProgress:
    tool_use_count: int = 0
    token_count: int = 0
    last_activity: Optional[ToolActivity] = None
    recent_activities: list[ToolActivity] = field(default_factory=list)
    summary: Optional[str] = None


@dataclass
class LocalAgentTaskState(TaskStateBase):
    type: TaskType = field(default="local_agent", init=False)
    agent_id: str = ""
    prompt: str = ""
    selected_agent: Optional[dict[str, Any]] = None
    agent_type: str = "subagent"
    model: Optional[str] = None
    abort_controller: Optional[Any] = None
    unregister_cleanup: Optional[Any] = None
    error: Optional[str] = None
    result: Optional[Any] = None
    progress: Optional[AgentProgress] = None
    retrieved: bool = False
    messages: Optional[list[Any]] = None
    last_reported_tool_count: int = 0
    last_reported_token_count: int = 0
    is_backgrounded: bool = True
    pending_messages: list[str] = field(default_factory=list)
    retain: bool = False
    disk_loaded: bool = False
    evict_after: Optional[float] = None
    output: str = ""
    agent_name: Optional[str] = None


@dataclass
class RemoteAgentTaskState(TaskStateBase):
    type: TaskType = field(default="remote_agent", init=False)
    remote_task_type: RemoteTaskType = "remote-agent"
    remote_task_metadata: Optional[dict[str, Any]] = None
    session_id: str = ""
    command: str = ""
    title: str = ""
    todo_list: list[dict[str, Any]] = field(default_factory=list)
    log: list[dict[str, Any]] = field(default_factory=list)
    is_long_running: bool = False
    poll_started_at: float = field(default_factory=lambda: time.time() * 1000)
    is_remote_review: bool = False
    review_progress: Optional[dict[str, Any]] = None
    is_ultraplan: bool = False
    ultraplan_phase: Optional[str] = None


@dataclass
class TeammateIdentity:
    agent_id: str
    agent_name: str
    team_name: str
    color: Optional[str] = None
    plan_mode_required: bool = False
    parent_session_id: str = ""


@dataclass
class InProcessTeammateTaskState(TaskStateBase):
    type: TaskType = field(default="in_process_teammate", init=False)
    identity: Optional[TeammateIdentity] = None
    prompt: str = ""
    model: Optional[str] = None
    selected_agent: Optional[dict[str, Any]] = None
    abort_controller: Optional[Any] = None
    current_work_abort_controller: Optional[Any] = None
    unregister_cleanup: Optional[Any] = None
    awaiting_plan_approval: bool = False
    permission_mode: str = "default"
    error: Optional[str] = None
    result: Optional[Any] = None
    progress: Optional[AgentProgress] = None
    messages: Optional[list[Any]] = None
    in_progress_tool_use_ids: Optional[set[str]] = None
    pending_user_messages: list[str] = field(default_factory=list)
    spinner_verb: Optional[str] = None
    past_tense_verb: Optional[str] = None
    is_idle: bool = False
    shutdown_requested: bool = False
    on_idle_callbacks: Optional[list[Any]] = None
    last_reported_tool_count: int = 0
    last_reported_token_count: int = 0


@dataclass
class DreamTurn:
    text: str
    tool_use_count: int = 0


@dataclass
class DreamTaskState(TaskStateBase):
    type: TaskType = field(default="dream", init=False)
    phase: Literal["starting", "updating"] = "starting"
    sessions_reviewing: int = 0
    files_touched: list[str] = field(default_factory=list)
    turns: list[DreamTurn] = field(default_factory=list)
    abort_controller: Optional[Any] = None
    prior_mtime: float = 0.0


@dataclass
class TodoTask(TaskStateBase):
    type: TaskType = field(default="todo", init=False)
    subject: str = ""
    active_form: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    blocks: list[str] = field(default_factory=list)
    blocked_by: list[str] = field(default_factory=list)
    owner: Optional[str] = None


TaskBase = TaskStateBase
ShellTask = LocalShellTaskState
AgentTask = LocalAgentTaskState

TaskState = (
    LocalShellTaskState
    | LocalAgentTaskState
    | RemoteAgentTaskState
    | InProcessTeammateTaskState
    | DreamTaskState
    | TodoTask
)

BackgroundTaskState = (
    LocalShellTaskState
    | LocalAgentTaskState
    | RemoteAgentTaskState
    | InProcessTeammateTaskState
    | DreamTaskState
)


def _get_field(task: Any, name: str, default: Any = None) -> Any:
    if isinstance(task, dict):
        return task.get(name, default)
    return getattr(task, name, default)


def is_background_task(task: TaskState) -> bool:
    if _get_field(task, "status") not in {"running", "pending"}:
        return False
    if _get_field(task, "is_backgrounded", True) is False:
        return False
    return True
