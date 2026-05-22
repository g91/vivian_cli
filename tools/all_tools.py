"""All built-in tool implementations for Vivian CLI.

Mirrors src/tools/* — every tool from the TypeScript codebase.
Delegates entirely to per-tool subdirectory packages. No inline handler logic here.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

from .registry import ToolRegistry
from ..types import ToolDefinition, ToolSource

# ── camelCase utils (re-exported for backward compat) ───────────────────────
from .utils import tagMessagesWithToolUseID, getToolUseIDFromParentMessage
tag_messages_with_tool_use_id = tagMessagesWithToolUseID
get_tool_use_id_from_parent_message = getToolUseIDFromParentMessage
from .shared.fuzzy import fuzzyFind
from .shared.DiffView import renderUnifiedDiff

# ── Sub-package imports: definitions + handlers ──────────────────────────────
# AgentTool
from .AgentTool.AgentTool import (
    TOOL_NAME as _AGENT_NAME, INPUT_SCHEMA as _AGENT_INPUT,
    OUTPUT_SCHEMA as _AGENT_OUTPUT,
)
from .AgentTool.AgentTool import call as _agent_call
from .AgentTool.constants import AGENT_TOOL_NAME, LEGACY_AGENT_TOOL_NAME

# AskUserQuestionTool
from .AskUserQuestionTool.AskUserQuestionTool import (
    TOOL_NAME as _ASK_NAME, INPUT_SCHEMA as _ASK_INPUT, OUTPUT_SCHEMA as _ASK_OUTPUT,
)
from .AskUserQuestionTool.AskUserQuestionTool import call as _ask_call

# BashTool
from .BashTool.BashTool import (
    TOOL_NAME as _BASH_NAME, INPUT_SCHEMA as _BASH_INPUT, OUTPUT_SCHEMA as _BASH_OUTPUT,
)
from .BashTool.BashTool import call as _bash_call
from .BashTool.toolName import BASH_TOOL_NAME

# BriefTool
from .BriefTool.BriefTool import (
    TOOL_NAME as _BRIEF_NAME, INPUT_SCHEMA as _BRIEF_INPUT,
)
from .BriefTool.BriefTool import call as _brief_call

# ConfigTool
from .ConfigTool.ConfigTool import (
    TOOL_NAME as _CONFIG_NAME, INPUT_SCHEMA as _CONFIG_INPUT,
)
from .ConfigTool.ConfigTool import call as _config_call

# EnterPlanModeTool
from .EnterPlanModeTool.EnterPlanModeTool import (
    TOOL_NAME as _ENTER_PLAN_NAME, INPUT_SCHEMA as _ENTER_PLAN_INPUT,
)
from .EnterPlanModeTool.EnterPlanModeTool import call as _enter_plan_call

# ExitPlanModeTool
from .ExitPlanModeTool.ExitPlanModeV2Tool import (
    TOOL_NAME as _EXIT_PLAN_NAME, INPUT_SCHEMA as _EXIT_PLAN_INPUT,
)
from .ExitPlanModeTool.ExitPlanModeV2Tool import call as _exit_plan_call

# EnterWorktreeTool
from .EnterWorktreeTool.EnterWorktreeTool import (
    TOOL_NAME as _ENTER_WORKTREE_NAME, INPUT_SCHEMA as _ENTER_WORKTREE_INPUT,
)
from .EnterWorktreeTool.EnterWorktreeTool import call as _enter_worktree_call

# ExitWorktreeTool
from .ExitWorktreeTool.ExitWorktreeTool import (
    TOOL_NAME as _EXIT_WORKTREE_NAME, INPUT_SCHEMA as _EXIT_WORKTREE_INPUT,
)
from .ExitWorktreeTool.ExitWorktreeTool import call as _exit_worktree_call

# FileEditTool
from .FileEditTool.FileEditTool import (
    TOOL_NAME as _FILE_EDIT_NAME, INPUT_SCHEMA as _FILE_EDIT_INPUT,
    OUTPUT_SCHEMA as _FILE_EDIT_OUTPUT,
)
from .FileEditTool.FileEditTool import call as _file_edit_call
from .FileEditTool.constants import FILE_EDIT_TOOL_NAME
from .FileEditTool.editFile import editFile  # re-export for direct use

# FileReadTool
from .FileReadTool.FileReadTool import (
    TOOL_NAME as _FILE_READ_NAME, INPUT_SCHEMA as _FILE_READ_INPUT,
    OUTPUT_SCHEMA as _FILE_READ_OUTPUT,
)
from .FileReadTool.FileReadTool import call as _file_read_call

# FileWriteTool
from .FileWriteTool.FileWriteTool import (
    TOOL_NAME as _FILE_WRITE_NAME, INPUT_SCHEMA as _FILE_WRITE_INPUT,
)
from .FileWriteTool.FileWriteTool import call as _file_write_call

# GlobTool
from .GlobTool.GlobTool import (
    TOOL_NAME as _GLOB_NAME, INPUT_SCHEMA as _GLOB_INPUT,
    OUTPUT_SCHEMA as _GLOB_OUTPUT,
)
from .GlobTool.GlobTool import call as _glob_call

# GrepTool
from .GrepTool.GrepTool import (
    TOOL_NAME as _GREP_NAME, INPUT_SCHEMA as _GREP_INPUT,
    OUTPUT_SCHEMA as _GREP_OUTPUT,
)
from .GrepTool.GrepTool import call as _grep_call

# ListMcpResourcesTool
from .ListMcpResourcesTool.ListMcpResourcesTool import (
    TOOL_NAME as _LIST_MCP_NAME, INPUT_SCHEMA as _LIST_MCP_INPUT,
)
from .ListMcpResourcesTool.ListMcpResourcesTool import call as _list_mcp_call

# LSPTool
from .LSPTool.LSPTool import (
    TOOL_NAME as _LSP_NAME, INPUT_SCHEMA as _LSP_INPUT,
)
from .LSPTool.LSPTool import call as _lsp_call

# McpAuthTool
from .McpAuthTool.McpAuthTool import (
    TOOL_NAME as _MCP_AUTH_NAME, INPUT_SCHEMA as _MCP_AUTH_INPUT,
)
from .McpAuthTool.McpAuthTool import call as _mcp_auth_call

# MCPTool (uses dynamic prefix for MCP server tool names)
from .MCPTool.MCPTool import (
    TOOL_NAME_PREFIX as _MCP_NAME_PREFIX, INPUT_SCHEMA as _MCP_INPUT,
)
from .MCPTool.MCPTool import call as _mcp_call
_MCP_NAME = "Mcp"  # Generic registration name for Vivian's registry

# NotebookEditTool
from .NotebookEditTool.NotebookEditTool import (
    TOOL_NAME as _NOTEBOOK_NAME, INPUT_SCHEMA as _NOTEBOOK_INPUT,
)
from .NotebookEditTool.NotebookEditTool import call as _notebook_call

# PowerShellTool
from .PowerShellTool.PowerShellTool import (
    TOOL_NAME as _POWERSHELL_NAME, INPUT_SCHEMA as _POWERSHELL_INPUT,
)
from .PowerShellTool.PowerShellTool import call as _powershell_call

# ReadMcpResourceTool
from .ReadMcpResourceTool.ReadMcpResourceTool import (
    TOOL_NAME as _READ_MCP_NAME, INPUT_SCHEMA as _READ_MCP_INPUT,
)
from .ReadMcpResourceTool.ReadMcpResourceTool import call as _read_mcp_call

# RemoteTriggerTool
from .RemoteTriggerTool.RemoteTriggerTool import (
    TOOL_NAME as _REMOTE_TRIGGER_NAME, INPUT_SCHEMA as _REMOTE_TRIGGER_INPUT,
)
from .RemoteTriggerTool.RemoteTriggerTool import call as _remote_trigger_call

# REPLTool
from .REPLTool.REPLTool import (
    TOOL_NAME as _REPL_NAME, INPUT_SCHEMA as _REPL_INPUT,
)
from .REPLTool.REPLTool import call as _repl_call

# ScheduleCronTool
from .ScheduleCronTool.ScheduleCronTool import (
    TOOL_NAME as _SCHEDULE_CRON_NAME, INPUT_SCHEMA as _SCHEDULE_CRON_INPUT,
)
from .ScheduleCronTool.ScheduleCronTool import call as _schedule_cron_call

# SendMessageTool
from .SendMessageTool.SendMessageTool import (
    TOOL_NAME as _SEND_MSG_NAME, INPUT_SCHEMA as _SEND_MSG_INPUT,
)
from .SendMessageTool.SendMessageTool import call as _send_msg_call

# SkillTool
from .SkillTool.SkillTool import (
    TOOL_NAME as _SKILL_NAME, INPUT_SCHEMA as _SKILL_INPUT,
)
from .SkillTool.SkillTool import call as _skill_call

# SleepTool
from .SleepTool.SleepTool import (
    TOOL_NAME as _SLEEP_NAME, INPUT_SCHEMA as _SLEEP_INPUT,
)
from .SleepTool.SleepTool import call as _sleep_call

# SyntheticOutputTool
from .SyntheticOutputTool.SyntheticOutputTool import (
    TOOL_NAME as _SYNTHETIC_NAME, INPUT_SCHEMA as _SYNTHETIC_INPUT,
)
from .SyntheticOutputTool.SyntheticOutputTool import call as _synthetic_call

# Task tools
from .TaskCreateTool.TaskCreateTool import (
    TOOL_NAME as _TASK_CREATE_NAME, INPUT_SCHEMA as _TASK_CREATE_INPUT,
)
from .TaskCreateTool.TaskCreateTool import call as _task_create_call
from .TaskGetTool.TaskGetTool import (
    TOOL_NAME as _TASK_GET_NAME, INPUT_SCHEMA as _TASK_GET_INPUT,
)
from .TaskGetTool.TaskGetTool import call as _task_get_call
from .TaskListTool.TaskListTool import (
    TOOL_NAME as _TASK_LIST_NAME, INPUT_SCHEMA as _TASK_LIST_INPUT,
)
from .TaskListTool.TaskListTool import call as _task_list_call
from .TaskOutputTool.TaskOutputTool import (
    TOOL_NAME as _TASK_OUTPUT_NAME, INPUT_SCHEMA as _TASK_OUTPUT_INPUT,
)
from .TaskOutputTool.TaskOutputTool import call as _task_output_call
from .TaskStopTool.TaskStopTool import (
    TOOL_NAME as _TASK_STOP_NAME, INPUT_SCHEMA as _TASK_STOP_INPUT,
)
from .TaskStopTool.TaskStopTool import call as _task_stop_call
from .TaskUpdateTool.TaskUpdateTool import (
    TOOL_NAME as _TASK_UPDATE_NAME, INPUT_SCHEMA as _TASK_UPDATE_INPUT,
)
from .TaskUpdateTool.TaskUpdateTool import call as _task_update_call

# TeamCreateTool
from .TeamCreateTool.TeamCreateTool import (
    TOOL_NAME as _TEAM_CREATE_NAME, INPUT_SCHEMA as _TEAM_CREATE_INPUT,
)
from .TeamCreateTool.TeamCreateTool import call as _team_create_call

# TeamDeleteTool
from .TeamDeleteTool.TeamDeleteTool import (
    TOOL_NAME as _TEAM_DELETE_NAME, INPUT_SCHEMA as _TEAM_DELETE_INPUT,
)
from .TeamDeleteTool.TeamDeleteTool import call as _team_delete_call

# TodoWriteTool
from .TodoWriteTool.TodoWriteTool import (
    TOOL_NAME as _TODO_NAME, INPUT_SCHEMA as _TODO_INPUT,
)
from .TodoWriteTool.TodoWriteTool import call as _todo_call

# ToolSearchTool
from .ToolSearchTool.ToolSearchTool import (
    TOOL_NAME as _TOOL_SEARCH_NAME, INPUT_SCHEMA as _TOOL_SEARCH_INPUT,
)
from .ToolSearchTool.ToolSearchTool import call as _tool_search_call

# WebFetchTool
from .WebFetchTool.WebFetchTool import (
    TOOL_NAME as _WEB_FETCH_NAME, INPUT_SCHEMA as _WEB_FETCH_INPUT,
)
from .WebFetchTool.WebFetchTool import call as _web_fetch_call

# WebSearchTool
from .WebSearchTool.WebSearchTool import (
    TOOL_NAME as _WEB_SEARCH_NAME, INPUT_SCHEMA as _WEB_SEARCH_INPUT,
)
from .WebSearchTool.WebSearchTool import call as _web_search_call

# CompileTool
from .CompileTool.CompileTool import (
    TOOL_NAME as _COMPILE_NAME, INPUT_SCHEMA as _COMPILE_INPUT,
    OUTPUT_SCHEMA as _COMPILE_OUTPUT,
)
from .CompileTool.CompileTool import call as _compile_call

# SSHTool
from .SSHTool.SSHTool import (
    TOOL_NAME as _SSH_NAME, INPUT_SCHEMA as _SSH_INPUT,
    OUTPUT_SCHEMA as _SSH_OUTPUT,
)
from .SSHTool.SSHTool import call as _ssh_call

# TryHackMeTool
from .TryHackMeTool.TryHackMeTool import (
    TOOL_NAME as _THM_NAME, INPUT_SCHEMA as _THM_INPUT,
    OUTPUT_SCHEMA as _THM_OUTPUT,
)
from .TryHackMeTool.TryHackMeTool import call as _thm_call

# VulnScannerTool
from .VulnScannerTool.VulnScannerTool import (
    TOOL_NAME as _VULN_SCAN_NAME, INPUT_SCHEMA as _VULN_SCAN_INPUT,
    OUTPUT_SCHEMA as _VULN_SCAN_OUTPUT,
)
from .VulnScannerTool.VulnScannerTool import call as _vuln_scan_call

# WebAuditTool
from .WebAuditTool.WebAuditTool import (
    TOOL_NAME as _WEB_AUDIT_NAME, INPUT_SCHEMA as _WEB_AUDIT_INPUT,
    OUTPUT_SCHEMA as _WEB_AUDIT_OUTPUT,
)
from .WebAuditTool.WebAuditTool import call as _web_audit_call

# CodeAuditTool
from .CodeAuditTool.CodeAuditTool import (
    TOOL_NAME as _CODE_AUDIT_NAME, INPUT_SCHEMA as _CODE_AUDIT_INPUT,
    OUTPUT_SCHEMA as _CODE_AUDIT_OUTPUT,
)
from .CodeAuditTool.CodeAuditTool import call as _code_audit_call

# AutoPentestTool
from .AutoPentestTool.AutoPentestTool import (
    TOOL_NAME as _AUTO_PWN_NAME, INPUT_SCHEMA as _AUTO_PWN_INPUT,
    OUTPUT_SCHEMA as _AUTO_PWN_OUTPUT,
)
from .AutoPentestTool.AutoPentestTool import call as _auto_pwn_call

# THMWriteupTool
from .THMWriteupTool.THMWriteupTool import (
    TOOL_NAME as _THM_WRITEUP_NAME, INPUT_SCHEMA as _THM_WRITEUP_INPUT,
    OUTPUT_SCHEMA as _THM_WRITEUP_OUTPUT,
)
from .THMWriteupTool.THMWriteupTool import call as _thm_writeup_call

# ParsecVisionTool
from .ParsecVisionTool.ParsecVisionTool import (
    TOOL_NAME as _PARSEC_VISION_NAME, INPUT_SCHEMA as _PARSEC_VISION_INPUT,
    OUTPUT_SCHEMA as _PARSEC_VISION_OUTPUT,
)
from .ParsecVisionTool.ParsecVisionTool import call as _parsec_vision_call

# DMAMemoryTool
from .DMAMemoryTool.DMAMemoryTool import (
    TOOL_NAME as _DMA_MEMORY_NAME, INPUT_SCHEMA as _DMA_MEMORY_INPUT,
    OUTPUT_SCHEMA as _DMA_MEMORY_OUTPUT,
)
from .DMAMemoryTool.DMAMemoryTool import call as _dma_memory_call

# RunScriptTool
from .RunScriptTool.RunScriptTool import (
    TOOL_NAME as _RUN_SCRIPT_NAME, INPUT_SCHEMA as _RUN_SCRIPT_INPUT,
    OUTPUT_SCHEMA as _RUN_SCRIPT_OUTPUT,
)
from .RunScriptTool.RunScriptTool import call as _run_script_call

logger = logging.getLogger(__name__)


# ── ToolDefinition builder ───────────────────────────────────────────────────

def _td(
    name: str,
    description: str,
    input_schema: dict,
    aliases: list[str] | None = None,
    requires_permission: bool = False,
    source: ToolSource = ToolSource.BUILTIN,
) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description=description,
        aliases=aliases or [],
        input_schema=input_schema,
        source=source,
        requires_permission=requires_permission,
    )


# ── Inline handlers for shared utilities exposed as tools ────────────────────

async def _fuzzy_find_handler(args: dict, context: Optional[dict] = None) -> dict:
    pattern = args.get("pattern", "")
    candidates = args.get("candidates", [])
    cutoff = args.get("cutoff", 0.6)
    results = fuzzyFind(pattern, candidates, cutoff=cutoff)
    return {"matches": results}


async def _render_diff_handler(args: dict, context: Optional[dict] = None) -> dict:
    original = args.get("original", "")
    modified = args.get("modified", "")
    file_path = args.get("file_path", "")
    diff = renderUnifiedDiff(original, modified, filePath=file_path)
    return {"diff": diff, "has_changes": diff != ""}


async def _list_directory_handler(args: dict, context: Optional[dict] = None) -> dict:
    raw_path = (
        args.get("path")
        or args.get("directory")
        or args.get("dir_path")
        or args.get("directory_path")
        or "."
    )
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        cwd = context.get("cwd", os.getcwd()) if isinstance(context, dict) else os.getcwd()
        path = Path(cwd) / path
    path = path.resolve()

    if not path.exists():
        return {"error": f"Path not found: {path}"}
    if not path.is_dir():
        return {"error": f"Not a directory: {path}"}

    try:
        entries = []
        for entry in sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
            name = entry.name + ("/" if entry.is_dir() else "")
            entries.append(name)
        return {"path": str(path), "entries": entries}
    except OSError as error:
        return {"error": str(error)}


# ── Tool definitions built from subdirectory schemas ────────────────────────
# Each entry: (ToolDefinition, handler_coroutine)
# Aliases include both the canonical name and common lowercase/alternate names
# so existing Vivian code that calls "bash", "file_read", etc. still resolves.

_TOOL_TABLE: list[tuple[ToolDefinition, Any]] = [
    (
        _td(_BASH_NAME, "Execute a bash shell command.",
            _BASH_INPUT,
            aliases=["bash", "shell", "run_command", "execute", "cmd", "terminal",
                     "run_bash", "execute_command"],
            requires_permission=True),
        _bash_call,
    ),
    (
        _td(_FILE_READ_NAME, "Read the contents of a file (text or image).",
            _FILE_READ_INPUT,
            aliases=["file_read", "read_file", "cat", "view_file", "open_file",
                     "get_file", "show_file", "view"]),
        _file_read_call,
    ),
    (
        _td(_FILE_WRITE_NAME, "Write content to a file, creating it if it does not exist.",
            _FILE_WRITE_INPUT,
            aliases=["file_write", "write_file", "create_file", "save_file",
                     "overwrite_file"],
            requires_permission=True),
        _file_write_call,
    ),
    (
        _td(_FILE_EDIT_NAME, "Edit a file by replacing an exact string with a new string.",
            _FILE_EDIT_INPUT,
            aliases=["file_edit", "Edit", "edit_file", "patch_file", "replace_in_file",
                     "str_replace"],
            requires_permission=True),
        _file_edit_call,
    ),
    (
        _td(_GLOB_NAME, "Find files matching a glob pattern.",
            _GLOB_INPUT,
            aliases=["glob", "find_files", "list_files_glob", "search_files"]),
        _glob_call,
    ),
    (
        _td(_GREP_NAME, "Search for a pattern in files using ripgrep/grep.",
            _GREP_INPUT,
            aliases=["grep", "search_text", "grep_search", "find_text",
                     "search_in_files", "rg"]),
        _grep_call,
    ),
    (
        _td(
            "ListDirectory",
            "List the contents of a directory.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to list"},
                    "directory": {"type": "string", "description": "Alias for path"},
                },
            },
            aliases=["list_directory", "list_dir", "read_directory", "directory_listing"],
        ),
        _list_directory_handler,
    ),
    (
        _td(_SLEEP_NAME, "Pause execution for a specified duration.",
            _SLEEP_INPUT,
            aliases=["sleep", "wait", "pause", "delay"]),
        _sleep_call,
    ),
    (
        _td(_WEB_FETCH_NAME, "Fetch content from a URL and extract the requested information.",
            _WEB_FETCH_INPUT,
            aliases=["web_fetch", "fetch_url", "http_get", "get_url", "fetch_page"]),
        _web_fetch_call,
    ),
    (
        _td(_WEB_SEARCH_NAME, "Search the web, optionally filtering by domain.",
            _WEB_SEARCH_INPUT,
            aliases=["web_search", "search_web", "internet_search", "search"]),
        _web_search_call,
    ),
    (
        _td(_TODO_NAME, "Create and manage a structured task list.",
            _TODO_INPUT,
            aliases=["todo_write", "TodoWrite", "manage_todos", "update_todos",
                     "set_todos", "task_list_write"]),
        _todo_call,
    ),
    (
        _td(_TASK_CREATE_NAME, "Create a new background task.",
            _TASK_CREATE_INPUT,
            aliases=["task_create", "create_task"],
            requires_permission=True),
        _task_create_call,
    ),
    (
        _td(_TASK_GET_NAME, "Get details of a specific task.",
            _TASK_GET_INPUT,
            aliases=["task_get", "get_task"]),
        _task_get_call,
    ),
    (
        _td(_TASK_LIST_NAME, "List all tasks.",
            _TASK_LIST_INPUT,
            aliases=["task_list", "list_tasks"]),
        _task_list_call,
    ),
    (
        _td(_TASK_UPDATE_NAME, "Update a task's status or details.",
            _TASK_UPDATE_INPUT,
            aliases=["task_update", "update_task"]),
        _task_update_call,
    ),
    (
        _td(_TASK_STOP_NAME, "Stop a running task.",
            _TASK_STOP_INPUT,
            aliases=["task_stop", "stop_task", "kill_task", "cancel_task"],
            requires_permission=True),
        _task_stop_call,
    ),
    (
        _td(_TASK_OUTPUT_NAME, "Get output from a background task.",
            _TASK_OUTPUT_INPUT,
            aliases=["task_output", "get_task_output"]),
        _task_output_call,
    ),
    (
        _td(_ASK_NAME, "Ask the user a question and get their response.",
            _ASK_INPUT,
            aliases=["ask_user_question", "AskUserQuestion", "ask_user",
                     "prompt_user", "get_user_input"]),
        _ask_call,
    ),
    (
        _td(_SKILL_NAME, "Execute a skill.",
            _SKILL_INPUT,
            aliases=["skill", "execute_skill", "run_skill",
                     "discover_skills", "DiscoverSkills"]),
        _skill_call,
    ),
    (
        _td(_AGENT_NAME, "Launch a sub-agent to work on a task.",
            _AGENT_INPUT,
            aliases=["agent", "Agent", "task", "Task", "sub_agent",
                     "spawn_agent", LEGACY_AGENT_TOOL_NAME]),
        _agent_call,
    ),
    (
        _td(_ENTER_PLAN_NAME, "Enter plan mode.",
            _ENTER_PLAN_INPUT,
            aliases=["enter_plan_mode", "plan_mode", "start_planning"]),
        _enter_plan_call,
    ),
    (
        _td(_EXIT_PLAN_NAME, "Exit plan mode and present the plan.",
            _EXIT_PLAN_INPUT,
            aliases=["exit_plan_mode", "submit_plan", "present_plan"]),
        _exit_plan_call,
    ),
    (
        _td(_ENTER_WORKTREE_NAME, "Enter a git worktree.",
            _ENTER_WORKTREE_INPUT,
            aliases=["enter_worktree"],
            requires_permission=True),
        _enter_worktree_call,
    ),
    (
        _td(_EXIT_WORKTREE_NAME, "Exit the current git worktree.",
            _EXIT_WORKTREE_INPUT,
            aliases=["exit_worktree"],
            requires_permission=True),
        _exit_worktree_call,
    ),
    (
        _td(_CONFIG_NAME, "Read or update configuration settings.",
            _CONFIG_INPUT,
            aliases=["config", "get_config", "set_config", "list_config"]),
        _config_call,
    ),
    (
        _td(_BRIEF_NAME, "Send a message to the user.",
            _BRIEF_INPUT,
            aliases=["brief", "Brief", "send_user_message", "SendUserMessage",
                     "send_message", "reply", "respond"]),
        _brief_call,
    ),
    (
        _td(_LIST_MCP_NAME, "List available MCP resources.",
            _LIST_MCP_INPUT,
            aliases=["list_mcp_resources", "mcp_list_resources"]),
        _list_mcp_call,
    ),
    (
        _td(_READ_MCP_NAME, "Read an MCP resource by URI.",
            _READ_MCP_INPUT,
            aliases=["read_mcp_resource", "mcp_read_resource"]),
        _read_mcp_call,
    ),
    (
        _td(_MCP_NAME, "Call a Model Context Protocol tool.",
            _MCP_INPUT,
            aliases=["mcp", "mcp_tool", "call_mcp"]),
        _mcp_call,
    ),
    (
        _td(_MCP_AUTH_NAME, "Authenticate with an MCP server.",
            _MCP_AUTH_INPUT,
            aliases=["mcp_auth", "mcp_authenticate"]),
        _mcp_auth_call,
    ),
    (
        _td(_LSP_NAME, "Interact with Language Server Protocol features.",
            _LSP_INPUT,
            aliases=["lsp", "go_to_definition", "find_references",
                     "get_hover", "get_diagnostics"]),
        _lsp_call,
    ),
    (
        _td(_TOOL_SEARCH_NAME, "Search for available tools.",
            _TOOL_SEARCH_INPUT,
            aliases=["tool_search", "search_tools", "find_tools"]),
        _tool_search_call,
    ),
    (
        _td(_NOTEBOOK_NAME, "Edit a Jupyter Notebook cell.",
            _NOTEBOOK_INPUT,
            aliases=["notebook_edit", "edit_notebook", "jupyter_edit"],
            requires_permission=True),
        _notebook_call,
    ),
    (
        _td(_REPL_NAME, "Execute code in an interactive REPL.",
            _REPL_INPUT,
            aliases=["repl", "python_repl", "code_repl", "jupyter",
                     "run_code", "execute_code"]),
        _repl_call,
    ),
    (
        _td(_SCHEDULE_CRON_NAME, "Schedule recurring tasks.",
            _SCHEDULE_CRON_INPUT,
            aliases=["schedule_cron", "cron", "schedule_task"],
            requires_permission=True),
        _schedule_cron_call,
    ),
    (
        _td(_SEND_MSG_NAME, "Send a message to the user.",
            _SEND_MSG_INPUT,
            aliases=["send_message_tool"]),
        _send_msg_call,
    ),
    (
        _td(_SYNTHETIC_NAME, "Emit synthetic output.",
            _SYNTHETIC_INPUT,
            aliases=["synthetic_output"]),
        _synthetic_call,
    ),
    (
        _td(_TEAM_CREATE_NAME, "Create a team of agents.",
            _TEAM_CREATE_INPUT,
            aliases=["team_create", "create_team"],
            requires_permission=True),
        _team_create_call,
    ),
    (
        _td(_TEAM_DELETE_NAME, "Delete a team.",
            _TEAM_DELETE_INPUT,
            aliases=["team_delete", "delete_team"],
            requires_permission=True),
        _team_delete_call,
    ),
    (
        _td(_POWERSHELL_NAME, "Execute a PowerShell command.",
            _POWERSHELL_INPUT,
            aliases=["powershell", "ps", "pwsh"],
            requires_permission=True),
        _powershell_call,
    ),
    (
        _td(_REMOTE_TRIGGER_NAME, "Trigger a remote action.",
            _REMOTE_TRIGGER_INPUT,
            aliases=["remote_trigger"],
            requires_permission=True),
        _remote_trigger_call,
    ),
    # ── CompileTool ──────────────────────────────────────────────────────────
    (
        _td(
            _COMPILE_NAME,
            "Compile C, C++, or other source code using the best available compiler "
            "(GCC, Clang, MSVC, etc.) on the current platform.",
            _COMPILE_INPUT,
            aliases=["compile", "compile_code", "build", "gcc", "clang", "make_binary"],
            requires_permission=True,
        ),
        _compile_call,
    ),
    # ── RunScriptTool ────────────────────────────────────────────────────────
    (
        _td(
            _RUN_SCRIPT_NAME,
            "Run a script (Python, JavaScript, Ruby, shell, PowerShell, etc.) and return "
            "its stdout, stderr, and exit code. Use this to test code and iterate on errors.",
            _RUN_SCRIPT_INPUT,
            aliases=[
                "run_script", "run_python", "test_script", "execute_script",
                "run_file", "python_run", "test_python", "run_code_file",
            ],
            requires_permission=True,
        ),
        _run_script_call,
    ),
    # ── SSHTool ──────────────────────────────────────────────────────────────
    (
        _td(
            _SSH_NAME,
            "SSH into remote servers for administration, file transfer, port forwarding, "
            "and security testing. Supports persistent connections, SCP file transfer, "
            "port scanning, SUID hunting, and system enumeration.",
            _SSH_INPUT,
            aliases=[
                "ssh", "ssh_exec", "ssh_connect", "remote_exec",
                "ssh_scan", "ssh_enum", "scp",
            ],
            requires_permission=True,
        ),
        _ssh_call,
    ),
    # ── TryHackMeTool ────────────────────────────────────────────────────────
    (
        _td(
            _THM_NAME,
            "Interact with TryHackMe CTF platform. Connect to TryHackMe VPN, "
            "run nmap/gobuster/nikto/hydra/sqlmap scans, enumerate SMB, crack hashes, "
            "upload linpeas for privilege escalation, and track captured flags.",
            _THM_INPUT,
            aliases=[
                "tryhackme", "thm", "ctf", "capture_the_flag",
                "thm_scan", "thm_enum", "thm_vpn", "thm_flag",
            ],
            requires_permission=True,
        ),
        _thm_call,
    ),
    # ── VulnScannerTool ──────────────────────────────────────────────────────
    (
        _td(
            _VULN_SCAN_NAME,
            "Multi-language SAST vulnerability scanner. Scan PHP, Java, Python, "
            "JavaScript, C/C++, Go, Ruby, and .NET code for SQL injection, XSS, "
            "command injection, path traversal, deserialization, SSRF, hardcoded "
            "secrets, weak crypto, and security misconfigurations. Each finding "
            "includes CWE ID and detailed remediation guidance.",
            _VULN_SCAN_INPUT,
            aliases=[
                "vuln_scanner", "vulnscan", "sast", "vuln_scan",
                "scan_vulns", "security_scan", "code_scan",
            ],
            requires_permission=True,
        ),
        _vuln_scan_call,
    ),
    # ── WebAuditTool ─────────────────────────────────────────────────────────
    (
        _td(
            _WEB_AUDIT_NAME,
            "Comprehensive web application vulnerability scanner covering the "
            "OWASP Top 10. Tests for SQL injection, XSS, CSRF, SSRF, path traversal, "
            "security headers, CORS misconfiguration, SSL/TLS issues, information "
            "disclosure, directory enumeration, cookie security, and API vulnerabilities. "
            "Produces detailed reports with evidence and remediation steps.",
            _WEB_AUDIT_INPUT,
            aliases=[
                "web_audit", "webaudit", "web_scanner", "web_scan",
                "website_audit", "web_vuln_scan", "owasp_scan",
            ],
            requires_permission=True,
        ),
        _web_audit_call,
    ),
    # ── CodeAuditTool ────────────────────────────────────────────────────────
    (
        _td(
            _CODE_AUDIT_NAME,
            "Deep code security audit with taint tracking, compliance checks, "
            "and prioritized remediation reports. Audits authentication, cryptography, "
            "input validation, session management, file operations, database interactions, "
            "and API endpoints. Supports OWASP ASVS compliance checking and generates "
            "fix reports with effort estimates.",
            _CODE_AUDIT_INPUT,
            aliases=[
                "code_audit", "codeaudit", "deep_audit", "code_review",
                "security_audit", "taint_track", "compliance_check",
            ],
            requires_permission=True,
        ),
        _code_audit_call,
    ),
    # ── AutoPentestTool ──────────────────────────────────────────────────────
    (
        _td(
            _AUTO_PWN_NAME,
            "Fully automated penetration testing framework. Performs autonomous "
            "end-to-end pentesting: port scanning, service fingerprinting, CVE "
            "cross-referencing against 100+ vulnerability entries, exploit search, "
            "and automated exploitation. Supports CTF (TryHackMe, VulnHub, HTB), "
            "King of the Hill, PHP/Java web exploitation, SMB/FTP/SSH attacks, "
            "and privilege escalation analysis. Includes a comprehensive vulnerability "
            "database covering Apache, Nginx, PHP, Java, SMB, SSH, FTP, MySQL, "
            "PostgreSQL, Redis, Jenkins, WordPress, Drupal, WebLogic, JBoss, Tomcat, "
            "Docker, Kubernetes, and 50+ more services.",
            _AUTO_PWN_INPUT,
            aliases=[
                "auto_pentest", "autopentest", "auto_pwn", "autopwn",
                "pentest", "pwn", "exploit", "hack", "kotb",
                "vulnhub", "end_match",
            ],
            requires_permission=True,
        ),
        _auto_pwn_call,
    ),
    # ── THMWriteupTool ───────────────────────────────────────────────────────
    (
        _td(
            _THM_WRITEUP_NAME,
            "TryHackMe write-up database and auto-exploit engine. Searches GitHub "
            "and the web for CTF write-ups, builds a local knowledge database, "
            "fingerprints target machines to identify which THM room they belong to, "
            "and auto-exploits based on known solutions. Optimized for King of the "
            "Hill speed runs with pre-loaded KOTH playbooks. Supports 70+ room "
            "fingerprints, GitHub repo/code search, web write-up scraping, and "
            "structured write-up parsing with flag extraction.",
            _THM_WRITEUP_INPUT,
            aliases=[
                "thm_writeup", "thmwriteup", "writeup_db", "writeup_search",
                "thm_db", "kotb_speedrun", "thm_auto", "auto_thm",
            ],
            requires_permission=True,
        ),
        _thm_writeup_call,
    ),
    # ── ParsecVisionTool ─────────────────────────────────────────────────────
    (
        _td(
            _PARSEC_VISION_NAME,
            "Real-time screen capture overlay with AI object detection. Captures "
            "the Parsec (or any) window, detects moving objects via frame "
            "differencing, draws bounding boxes and labels using an OpenGL overlay, "
            "and matches screen regions against a user-curated image database for "
            "identification. Supports motion detection, multi-scale template matching, "
            "annotated screenshots, and configurable sensitivity/FPS.",
            _PARSEC_VISION_INPUT,
            aliases=[
                "parsec_vision", "parsecvision", "vision_overlay",
                "screen_vision", "object_detect", "parsec_detect",
            ],
            requires_permission=True,
        ),
        _parsec_vision_call,
    ),
    # ── DMAMemoryTool ────────────────────────────────────────────────────────
    (
        _td(
            _DMA_MEMORY_NAME,
            "PCILeech FPGA DMA memory scanner for 75T/35T/ScreamerM2 cards. "
            "Scans process memory for integers, floats, strings, and byte patterns. "
            "Supports exact/range/unknown/changed/increased/decreased scans, "
            "AoB pattern matching with wildcards, pointer chain resolution, "
            "and value freezing (Cheat Engine-style memory hacking via DMA).",
            _DMA_MEMORY_INPUT,
            aliases=[
                "dma_memory", "dmamemory", "dma_scan", "dma_cheat",
                "memory_scan", "memscan", "dma_hack", "pcileech",
            ],
            requires_permission=True,
        ),
        _dma_memory_call,
    ),
    # Fuzzy find (shared utility exposed as a tool)
    (
        _td(
            "FuzzyFind",
            "Find files or items using fuzzy matching.",
            {
                "type": "object",
                "required": ["pattern", "candidates"],
                "properties": {
                    "pattern": {"type": "string"},
                    "candidates": {"type": "array", "items": {"type": "string"}},
                    "cutoff": {"type": "number", "default": 0.6},
                },
            },
            aliases=["fuzzy_find", "fuzzy_search"],
        ),
        _fuzzy_find_handler,
    ),
    # Render diff (shared utility exposed as a tool)
    (
        _td(
            "RenderDiff",
            "Render a unified diff between two strings.",
            {
                "type": "object",
                "required": ["original", "modified"],
                "properties": {
                    "original": {"type": "string"},
                    "modified": {"type": "string"},
                    "file_path": {"type": "string"},
                },
            },
            aliases=["render_diff"],
        ),
        _render_diff_handler,
    ),
]



# ── Register all tools ───────────────────────────────────────────────────────

def register_all_tools(registry: ToolRegistry) -> ToolRegistry:
    """Register all built-in tools with their handlers.
    
    Uses the new per-tool subdirectory packages exclusively.
    All inline definitions have been removed.
    """
    for tool_def, handler in _TOOL_TABLE:
        registry.register(tool_def, handler)
    return registry
