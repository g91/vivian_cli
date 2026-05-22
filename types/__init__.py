"""Types package — mirrors src/types/."""
from .ids import SessionId, AgentId, as_session_id, as_agent_id, to_agent_id
from .ids import asSessionId, asAgentId, toAgentId
from .permissions import (
    EXTERNAL_PERMISSION_MODES, INTERNAL_PERMISSION_MODES, PERMISSION_MODES,
    ExternalPermissionMode, PermissionMode, PermissionBehavior,
    PermissionRuleSource, PermissionRuleValue, PermissionRule,
    PermissionUpdateDestination, PermissionUpdate, PermissionDecision, PermissionResult,
)
from .plugin import (
    PluginAuthor, CommandMetadata, PluginManifest, BuiltinPluginDefinition,
    PluginRepository, PluginConfig, LoadedPlugin, PluginComponent, PluginError,
    PluginLoadResult, getPluginErrorMessage,
)
from .hooks import (
    HOOK_EVENTS, HookEvent, is_hook_event,
    isHookEvent, PromptRequest, PromptResponse, SyncHookResponse, AsyncHookResponse,
    HookResult, AggregatedHookResult,
)
from .command import (
    LocalCommandResult, TextResult, SkipResult, CompactResult,
    PromptCommand, LocalCommandCall, getCommandName, isCommandEnabled,
)
from .logs import (
    SerializedMessage, LogOption, SummaryMessage, CustomTitleMessage, AiTitleMessage,
    LastPromptMessage, TaskSummaryMessage, TagMessage, AgentNameMessage,
    AgentColorMessage, AgentSettingMessage, PRLinkMessage, sortLogs,
)
from .textInputTypes import (
    InlineGhostText, BaseTextInputProps, VimTextInputProps,
    VimMode as TextInputVimMode, BaseInputState, TextInputState, VimInputState,
    PromptInputMode, EditablePromptInputMode, QueuePriority, QueuedCommand,
    isValidImagePaste, getImagePasteIds,
)

# Keep backward-compatible bare imports
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union, Literal


class TaskType(str, Enum):
    LOCAL_BASH = "local_bash"
    LOCAL_AGENT = "local_agent"
    REMOTE_AGENT = "remote_agent"
    IN_PROCESS_TEAMMATE = "in_process_teammate"
    LOCAL_WORKFLOW = "local_workflow"
    MONITOR_MCP = "monitor_mcp"
    DREAM = "dream"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


class PermissionMode(str, Enum):
    DEFAULT = "default"
    ACCEPT_EDITS = "acceptEdits"
    BYPASS_PERMISSIONS = "bypassPermissions"
    PLAN = "plan"


class ToolSource(str, Enum):
    BUILTIN = "builtin"
    PLUGIN = "plugin"
    MCP = "mcp"
    SKILL = "skill"


class CommandType(str, Enum):
    PROMPT = "prompt"
    LOCAL = "local"
    LOCAL_JSX = "local_jsx"


class QuerySource(str, Enum):
    REPL_MAIN = "repl_main_thread"
    AGENT = "agent"
    HEADLESS = "headless"
    SDK = "sdk"


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    source: ToolSource = ToolSource.BUILTIN
    aliases: list[str] = field(default_factory=list)
    is_enabled: bool = True
    requires_permission: bool = True
    mcp_info: Optional[dict[str, str]] = None


@dataclass
class CommandDefinition:
    name: str
    description: str
    type: CommandType
    source: str = "builtin"
    aliases: list[str] = field(default_factory=list)
    content_length: int = 0
    progress_message: str = ""
    is_enabled: bool = True
    loaded_from: Optional[str] = None
    disable_model_invocation: bool = False


@dataclass
class Message:
    role: str  # "user", "assistant", "system", "tool"
    content: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class ChatCompletionChoice:
    index: int
    message: Message
    finish_reason: Optional[str] = None


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ChatCompletionResponse:
    id: str
    object: str = "chat.completion"
    created: int = 0
    model: str = ""
    choices: list[ChatCompletionChoice] = field(default_factory=list)
    usage: Optional[Usage] = None


@dataclass
class StreamChunk:
    id: str
    object: str = "chat.completion.chunk"
    created: int = 0
    model: str = ""
    choices: list[dict[str, Any]] = field(default_factory=list)
    usage: Optional[dict[str, Any]] = None  # populated on final chunk when stream_options.include_usage=true


@dataclass
class TaskState:
    id: str
    type: TaskType
    status: TaskStatus
    description: str
    tool_use_id: Optional[str] = None
    start_time: float = 0.0
    end_time: Optional[float] = None
    total_paused_ms: int = 0
    output_file: str = ""
    output_offset: int = 0
    notified: bool = False


@dataclass
class AppState:
    permission_mode: PermissionMode = PermissionMode.DEFAULT
    messages: list[Message] = field(default_factory=list)
    tasks: dict[str, TaskState] = field(default_factory=dict)
    current_model: str = "qwen3.6:latest"
    session_id: str = ""
    total_cost_usd: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_lines_added: int = 0
    total_lines_removed: int = 0
    is_auto_mode: bool = False
    is_fast_mode: bool = False
    is_plan_mode: bool = False


@dataclass
class CostState:
    total_cost_usd: float = 0.0
    total_api_duration: float = 0.0
    total_tool_duration: float = 0.0
    total_lines_added: int = 0
    total_lines_removed: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_cache_creation_tokens: int = 0
    total_web_search_requests: int = 0
    model_usage: dict[str, dict[str, Any]] = field(default_factory=dict)
    has_unknown_model_cost: bool = False


@dataclass
class QueryParams:
    messages: list[Message]
    system_prompt: str
    user_context: dict[str, str]
    system_context: dict[str, str]
    model: str = "qwen3.6:latest"
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    stream: bool = False
    tools: Optional[list[dict[str, Any]]] = None
    tool_choice: str = "auto"
    max_turns: int = 25
    query_source: QuerySource = QuerySource.REPL_MAIN
    task_budget: Optional[dict[str, int]] = None
    username: Optional[str] = None


@dataclass
class SkillDefinition:
    name: str
    description: str
    prompt: str
    source: str = "bundled"
    is_enabled: bool = True
    triggers: list[str] = field(default_factory=list)


@dataclass
class PluginDefinition:
    name: str
    version: str
    description: str
    tools: list[ToolDefinition] = field(default_factory=list)
    commands: list[CommandDefinition] = field(default_factory=list)
    skills: list[SkillDefinition] = field(default_factory=list)
    hooks: dict[str, Any] = field(default_factory=dict)


@dataclass
class HookDefinition:
    name: str
    event: str  # "pre_tool_use", "post_tool_use", "session_start", etc.
    handler: str
    is_enabled: bool = True


@dataclass
class Keybinding:
    key: str
    command: str
    description: str = ""
    context: str = "global"


@dataclass
class VimState:
    mode: str = "normal"  # normal, insert, visual, visual-line, operator-pending
    register: str = ""
    operator: Optional[str] = None
    count: Optional[int] = None
    last_change: Optional[str] = None


@dataclass
class BridgeConfig:
    enabled: bool = False
    url: str = ""
    auth_token: str = ""
    session_id: str = ""
    poll_interval_ms: int = 2000


@dataclass
class BuddyState:
    name: str = "vivian"
    sprite: str = "default"
    mood: str = "neutral"
    notifications_enabled: bool = True
