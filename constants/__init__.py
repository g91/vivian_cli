"""Constants for Vivian CLI — mirrors src/constants/."""

# Re-export from sub-modules
from .product import (
    PRODUCT_URL,
    vivian_AI_BASE_URL, vivian_AI_STAGING_BASE_URL, vivian_AI_LOCAL_BASE_URL,
    isRemoteSessionStaging, isRemoteSessionLocal, getvivianAiBaseUrl, getRemoteSessionUrl,
)
from .errorIds import E_TOOL_USE_SUMMARY_GENERATION_FAILED
from .common import getLocalISODate, getSessionStartDate, getLocalMonthYear
from .apiLimits import (
    API_IMAGE_MAX_BASE64_SIZE, IMAGE_TARGET_RAW_SIZE, IMAGE_MAX_WIDTH, IMAGE_MAX_HEIGHT,
    PDF_TARGET_RAW_SIZE, API_PDF_MAX_PAGES, PDF_EXTRACT_SIZE_THRESHOLD,
    PDF_MAX_EXTRACT_SIZE, PDF_MAX_PAGES_PER_READ, PDF_AT_MENTION_INLINE_THRESHOLD,
    API_MAX_MEDIA_PER_REQUEST,
)
from .betas import (
    vivian_CODE_20250219_BETA_HEADER, INTERLEAVED_THINKING_BETA_HEADER,
    CONTEXT_1M_BETA_HEADER, CONTEXT_MANAGEMENT_BETA_HEADER,
    STRUCTURED_OUTPUTS_BETA_HEADER, WEB_SEARCH_BETA_HEADER,
    TOOL_SEARCH_BETA_HEADER_1P, TOOL_SEARCH_BETA_HEADER_3P,
    EFFORT_BETA_HEADER, TASK_BUDGETS_BETA_HEADER,
    PROMPT_CACHING_SCOPE_BETA_HEADER, FAST_MODE_BETA_HEADER,
    REDACT_THINKING_BETA_HEADER, TOKEN_EFFICIENT_TOOLS_BETA_HEADER,
    ADVISOR_BETA_HEADER,
    BEDROCK_EXTRA_PARAMS_HEADERS, VERTEX_COUNT_TOKENS_ALLOWED_BETAS,
)
from .cyberRiskInstruction import CYBER_RISK_INSTRUCTION
from .figures import (
    BLACK_CIRCLE, BULLET_OPERATOR, TEARDROP_ASTERISK,
    UP_ARROW, DOWN_ARROW, LIGHTNING_BOLT,
    EFFORT_LOW, EFFORT_MEDIUM, EFFORT_HIGH, EFFORT_MAX,
    PLAY_ICON, PAUSE_ICON, REFRESH_ARROW, CHANNEL_ARROW, INJECTED_ARROW,
    FORK_GLYPH, DIAMOND_OPEN, DIAMOND_FILLED, REFERENCE_MARK,
    FLAG_ICON, BLOCKQUOTE_BAR, HEAVY_HORIZONTAL,
    BRIDGE_SPINNER_FRAMES, BRIDGE_READY_INDICATOR, BRIDGE_FAILED_INDICATOR,
)
from .files import (
    BINARY_EXTENSIONS, BINARY_CHECK_SIZE,
    hasBinaryExtension, isBinaryContent,
)
from .github_app import PR_TITLE, GITHUB_ACTION_SETUP_DOCS_URL, WORKFLOW_CONTENT
from .keys import GROWTHBOOK_KEYS
from .messages import MAX_MESSAGE_LENGTH, MAX_TOOL_RESULT_LENGTH, MAX_SYSTEM_MESSAGE_LENGTH
from .outputStyles import OUTPUT_STYLE_DIR_NAME, OUTPUT_STYLE_FILE_EXTENSION
from .prompts import DEFAULT_SYSTEM_PROMPT, DEFAULT_AGENT_PROMPT
from .spinnerVerbs import SPINNER_VERBS, getSpinnerVerbs
from .system import (
    PRODUCT_NAME, PRODUCT_VERSION,
    DEFAULT_BASE_URL, DEFAULT_MODEL, DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE, DEFAULT_TOP_P, DEFAULT_MAX_TURNS,
    MAX_OUTPUT_TOKENS_RECOVERY_LIMIT, ERROR_IDS,
    FRONTIER_MODEL_NAME, vivian_4_5_OR_4_6_MODEL_IDS,
    getCwd, getIsGit, getUnameSR, getShellInfoLine, getKnowledgeCutoff,
    computeEnvInfo, enhanceSystemPromptWithEnvDetails,
)
from .systemPromptSections import SYSTEM_PROMPT_SECTIONS
from .toolLimits import (
    MAX_BASH_OUTPUT_LENGTH, MAX_FILE_READ_SIZE,
    MAX_GLOB_RESULTS, MAX_GREP_RESULTS, MAX_FILE_WRITE_SIZE,
)
from .tools import (
    BASH_TOOL_NAME, FILE_READ_TOOL_NAME, FILE_WRITE_TOOL_NAME,
    FILE_EDIT_TOOL_NAME, GLOB_TOOL_NAME, GREP_TOOL_NAME,
    NOTEBOOK_EDIT_TOOL_NAME, TOOL_SEARCH_TOOL_NAME,
    SLEEP_TOOL_NAME, DISCOVER_SKILLS_TOOL_NAME, TICK_TAG,
)
from .turnCompletionVerbs import TURN_COMPLETION_VERBS
from .xml import TOOL_USE_TAG, TOOL_RESULT_TAG, THINKING_TAG, RESPONSE_TAG, ENV_TAG

# Vivian-specific overrides
DEFAULT_API_VERSION = "v1"
REQUEST_TIMEOUT = 600
MAX_STATUS_CHARS = 2000
MAX_HISTORY_ITEMS = 100
MAX_PASTED_CONTENT_LENGTH = 1024

TASK_ID_PREFIXES = {
    "local_bash": "b",
    "local_agent": "a",
    "remote_agent": "r",
    "in_process_teammate": "t",
    "local_workflow": "w",
    "monitor_mcp": "m",
    "dream": "d",
}

TOOL_PRESETS = ["default"]

ALL_BASE_TOOLS = [
    "agent", "task_output", "bash", "glob", "grep", "list_directory", "exit_plan_mode",
    "file_read", "file_edit", "file_write", "notebook_edit",
    "web_fetch", "todo_write", "web_search", "task_stop",
    "ask_user_question", "skill", "enter_plan_mode", "config",
    "brief", "list_mcp_resources", "read_mcp_resource", "tool_search",
    "ssh", "tryhackme", "vulnscanner", "webaudit", "codeaudit",
    "autopentest", "thmwriteup", "parsecvision", "dmamemory",
]

ALL_AGENT_DISALLOWED_TOOLS = [
    "agent", "task_output", "exit_plan_mode", "enter_plan_mode",
    "ask_user_question", "skill",
]

COORDINATOR_MODE_ALLOWED_TOOLS = [
    "agent", "task_output", "bash", "glob", "grep", "list_directory",
    "file_read", "file_edit", "file_write", "web_fetch",
    "web_search", "todo_write", "task_stop",
]

REMOTE_SAFE_COMMANDS = [
    "session", "exit", "clear", "help", "theme", "color",
    "vim", "cost", "usage", "copy", "btw", "feedback",
    "plan", "keybindings", "statusline", "stickers", "mobile",
]

BRIDGE_SAFE_COMMANDS = [
    "compact", "clear", "cost", "summary", "releaseNotes", "files",
]

# Vivian-specific overrides
DEFAULT_API_VERSION = "v1"
REQUEST_TIMEOUT = 600
MAX_STATUS_CHARS = 2000
MAX_HISTORY_ITEMS = 100
MAX_PASTED_CONTENT_LENGTH = 1024

OUTPUT_STYLES = ["default", "concise", "detailed", "explain"]

OAUTH_SCOPES = ["read", "write", "admin"]
OAUTH_TOKEN_URL = "/api/oauth/token"

GITHUB_APP_NAME = "vivian-cli"
GITHUB_APP_SCOPES = ["repo", "workflow", "read:org"]

AVAILABLE_BETAS = [
    "agent_swarms", "worktree_mode", "voice_mode",
    "bridge_mode", "coordinator_mode", "proactive", "kairos",
]

PROMPT_TEMPLATES = {
    "system_identity": "You are Vivian, an AI assistant.",
    "tool_use_instructions": "You have access to the following tools.",
    "memory_instructions": "You can read and write to persistent memory.",
    "git_instructions": "You are working in a git repository.",
    "code_style": "Write clean, idiomatic code with proper error handling.",
    "safety": "Never execute destructive commands without confirmation.",
}
