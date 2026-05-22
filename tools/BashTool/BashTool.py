"""
BashTool — mirrors src/tools/BashTool/BashTool.tsx

Executes bash commands in a persistent shell session.
"""
from __future__ import annotations
import asyncio
import os
import re
import subprocess
import tempfile
from typing import Any, AsyncGenerator, Dict, List, Optional, Set

from .toolName import BASH_TOOL_NAME
from .commandSemantics import interpretCommandResult
from .commentLabel import extractBashCommentLabel
from .destructiveCommandWarning import getDestructiveCommandWarning
from .modeValidation import checkPermissionMode
from .prompt import getDefaultTimeoutMs, getMaxTimeoutMs, getSimplePrompt
from .shouldUseSandbox import shouldUseSandbox
from ...services.analytics import logEvent
from ...utils.codeIndexing import detectCodeIndexingFromCommand
from ...utils.file import detectFileEncoding, detectLineEndings, getFileModificationTime, writeTextContent

TOOL_NAME = BASH_TOOL_NAME

# Search commands for collapsible display
BASH_SEARCH_COMMANDS: Set[str] = {"find", "grep", "rg", "ag", "ack", "locate", "which", "whereis"}
BASH_READ_COMMANDS: Set[str] = {"cat", "head", "tail", "less", "more", "wc", "stat", "file",
                                  "strings", "jq", "awk", "cut", "sort", "uniq", "tr"}
BASH_LIST_COMMANDS: Set[str] = {"ls", "tree", "du"}
BASH_SEMANTIC_NEUTRAL_COMMANDS: Set[str] = {"echo", "printf", "true", "false", ":"}
BASH_SILENT_COMMANDS: Set[str] = {"mv", "cp", "rm", "mkdir", "rmdir", "chmod", "chown",
                                   "chgrp", "touch", "ln", "cd", "export", "unset", "wait"}

INPUT_SCHEMA = {
    "type": "object",
    "required": ["command"],
    "properties": {
        "command": {"type": "string", "description": "The command to execute"},
        "timeout": {
            "type": "number",
            "description": f"Optional timeout in milliseconds (max {getMaxTimeoutMs()})",
        },
        "description": {
            "type": "string",
            "description": "Clear, concise description of what this command does",
        },
        "run_in_background": {
            "type": "boolean",
            "description": "Set to true to run this command in the background.",
        },
        "dangerouslyDisableSandbox": {
            "type": "boolean",
            "description": "Set to true to dangerously override sandbox mode.",
        },
        "_simulatedSedEdit": {
            "type": "object",
            "properties": {
                "filePath": {"type": "string"},
                "newContent": {"type": "string"},
            },
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "stdout": {"type": "string"},
        "stderr": {"type": "string"},
        "interrupted": {"type": "boolean"},
        "isImage": {"type": "boolean"},
        "backgroundTaskId": {"type": "string"},
        "returnCodeInterpretation": {"type": "string"},
        "noOutputExpected": {"type": "boolean"},
    },
}


def isSearchOrReadBashCommand(command: str) -> Dict[str, bool]:
    """
    Checks if a bash command is a search or read operation.
    Returns dict with isSearch, isRead, isList keys.
    """
    import re
    parts = re.split(r"[|;&]", command)
    hasSearch = False
    hasRead = False
    hasList = False
    hasNonNeutralCommand = False

    for part in parts:
        baseCommand = part.strip().split()[0] if part.strip() else ""
        if not baseCommand:
            continue
        if baseCommand in BASH_SEMANTIC_NEUTRAL_COMMANDS:
            continue
        hasNonNeutralCommand = True
        isPartSearch = baseCommand in BASH_SEARCH_COMMANDS
        isPartRead = baseCommand in BASH_READ_COMMANDS
        isPartList = baseCommand in BASH_LIST_COMMANDS
        if not (isPartSearch or isPartRead or isPartList):
            return {"isSearch": False, "isRead": False, "isList": False}
        if isPartSearch:
            hasSearch = True
        if isPartRead:
            hasRead = True
        if isPartList:
            hasList = True

    if not hasNonNeutralCommand:
        return {"isSearch": False, "isRead": False, "isList": False}
    return {"isSearch": hasSearch, "isRead": hasRead, "isList": hasList}


def detectBlockedSleepPattern(command: str) -> Optional[str]:
    """Detect standalone sleep patterns that should use Monitor instead."""
    import re
    parts = re.split(r"[|;&]", command)
    if not parts:
        return None
    first = parts[0].strip()
    m = re.match(r"^sleep\s+(\d+)\s*$", first)
    if not m:
        return None
    secs = int(m.group(1))
    if secs < 2:
        return None
    rest = " ".join(p.strip() for p in parts[1:]).strip()
    return f"sleep {secs} followed by: {rest}" if rest else f"standalone sleep {secs}"


async def description() -> str:
    return "Run shell commands with persistent state across calls."


async def prompt() -> str:
    return getSimplePrompt()


def userFacingName() -> str:
    return ""


def getToolUseSummary(input_data: Dict[str, Any]) -> str:
    label = extractBashCommentLabel(input_data.get("command", ""))
    return label or input_data.get("description") or input_data.get("command", "")[:60]


def getActivityDescription(input_data: Dict[str, Any]) -> str:
    return getToolUseSummary(input_data)


_CD_RE = re.compile(r'^\s*cd(?:\s+(.+?))?\s*$')


def _handle_cd(target: Optional[str], base_cwd: str, context: Any) -> Dict[str, Any]:
    """Apply a bare `cd` to the Python process cwd so it persists across tool calls."""
    if target is None or target.strip() == "~":
        new_dir = os.path.expanduser("~")
    elif target.strip() == "-":
        prev = os.environ.get("OLDPWD")
        if not prev:
            return {"stdout": "", "stderr": "cd: OLDPWD not set",
                    "interrupted": False, "isImage": False}
        new_dir = prev
    else:
        t = target.strip()
        if len(t) >= 2 and ((t[0] == '"' and t[-1] == '"') or (t[0] == "'" and t[-1] == "'")):
            t = t[1:-1]
        t = os.path.expanduser(os.path.expandvars(t))
        new_dir = t if os.path.isabs(t) else os.path.normpath(os.path.join(base_cwd, t))

    if not os.path.isdir(new_dir):
        return {"stdout": "", "stderr": f"cd: {new_dir}: No such file or directory",
                "interrupted": False, "isImage": False}

    old = os.getcwd()
    try:
        os.chdir(new_dir)
    except OSError as e:
        return {"stdout": "", "stderr": f"cd: {e}",
                "interrupted": False, "isImage": False}
    os.environ["OLDPWD"] = old
    os.environ["PWD"] = os.getcwd()
    if isinstance(context, dict):
        context["cwd"] = os.getcwd()
    return {"stdout": os.getcwd() + "\n", "stderr": "",
            "interrupted": False, "isImage": False,
            "returnCodeInterpretation": None, "noOutputExpected": False}


def _dbg(msg: str) -> None:
    if os.environ.get("VIVIAN_DEBUG"):
        try:
            with open(os.path.expanduser("~/.vivian_cli_debug.log"), "a") as f:
                import time
                f.write(f"[{time.strftime('%H:%M:%S')}] BashTool: {msg}\n")
        except Exception:
            pass


async def _apply_simulated_sed_edit(simulated_edit: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    file_path = str(simulated_edit.get("filePath") or "")
    new_content = str(simulated_edit.get("newContent") or "")
    if not file_path:
        return {"stdout": "", "stderr": "sed: missing file path\nExit code 1", "interrupted": False, "isImage": False}
    absolute_file_path = os.path.abspath(os.path.expanduser(file_path))
    try:
        encoding = detectFileEncoding(absolute_file_path)
        with open(absolute_file_path, "r", encoding=encoding, errors="replace", newline="") as handle:
            handle.read()
    except FileNotFoundError:
        return {
            "stdout": "",
            "stderr": f"sed: {file_path}: No such file or directory\nExit code 1",
            "interrupted": False,
            "isImage": False,
        }

    endings = detectLineEndings(absolute_file_path)
    writeTextContent(absolute_file_path, new_content, encoding, endings)
    read_file_state = context.get("readFileState") if isinstance(context, dict) else None
    if hasattr(read_file_state, "set"):
        read_file_state.set(
            absolute_file_path,
            {
                "content": new_content,
                "timestamp": getFileModificationTime(absolute_file_path),
                "offset": None,
                "limit": None,
            },
        )
    elif isinstance(read_file_state, dict):
        read_file_state[absolute_file_path] = {
            "content": new_content,
            "timestamp": getFileModificationTime(absolute_file_path),
            "offset": None,
            "limit": None,
        }
    return {
        "stdout": "",
        "stderr": "",
        "interrupted": False,
        "isImage": False,
        "returnCodeInterpretation": None,
        "noOutputExpected": True,
    }


async def call(
    input_data: Dict[str, Any],
    context: Any = None,
    timeout_ms: Optional[int] = None,
) -> Dict[str, Any]:
    """Execute a bash command and return the result."""
    if isinstance(input_data.get("_simulatedSedEdit"), dict):
        return await _apply_simulated_sed_edit(input_data["_simulatedSedEdit"], context)

    command = (
        input_data.get("command")
        or input_data.get("cmd")
        or input_data.get("shell_command")
        or input_data.get("bash_command")
        or ""
    )
    _dbg(f"call() command={command!r} cwd={os.getcwd()} ctx_cwd={context.get('cwd') if isinstance(context, dict) else None}")
    timeout_sec = (timeout_ms or input_data.get("timeout") or getDefaultTimeoutMs()) / 1000
    timeout_sec = min(timeout_sec, getMaxTimeoutMs() / 1000)

    # Intercept bare `cd` so it actually changes the working directory of this
    # process (subprocess cd would have no effect on the parent).
    cd_match = _CD_RE.match(command)
    if cd_match:
        base = context.get("cwd") if isinstance(context, dict) else os.getcwd()
        result = _handle_cd(cd_match.group(1), base or os.getcwd(), context)
        _dbg(f"  cd handled → new cwd={os.getcwd()} result={result}")
        return result

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=context.get("cwd") if isinstance(context, dict) else None,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_sec
            )
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            exitCode = proc.returncode or 0
            interrupted = False
        except asyncio.TimeoutError:
            proc.kill()
            stdout = ""
            stderr = f"Command timed out after {int(timeout_sec)}s"
            exitCode = 124
            interrupted = True

        semantics = interpretCommandResult(command, exitCode, stdout, stderr)
        command_type = command.split(" ", 1)[0] if command else ""
        logEvent(
            "tengu_bash_tool_command_executed",
            {
                "command_type": command_type,
                "stdout_length": len(stdout),
                "stderr_length": len(stderr),
                "exit_code": exitCode,
                "interrupted": interrupted,
            },
        )

        code_indexing_tool = detectCodeIndexingFromCommand(command)
        if code_indexing_tool:
            logEvent(
                "tengu_code_indexing_tool_used",
                {
                    "tool": code_indexing_tool,
                    "source": "cli",
                    "success": exitCode == 0,
                },
            )

        return {
            "stdout": stdout,
            "stderr": stderr,
            "interrupted": interrupted,
            "isImage": False,
            "returnCodeInterpretation": semantics.get("message"),
            "noOutputExpected": not stdout.strip() and exitCode == 0,
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "interrupted": False,
            "isImage": False,
        }
