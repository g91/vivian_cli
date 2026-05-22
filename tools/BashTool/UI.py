"""BashTool UI rendering — mirrors src/tools/BashTool/UI.tsx"""
from __future__ import annotations
from typing import Any, Dict, Optional
from .commentLabel import extractBashCommentLabel
from .sedEditParser import parseSedEditCommand
from ...utils.file import getDisplayPath


class BackgroundHint:
    """Hint that a command is running in the background."""
    def __init__(self, taskId: str):
        self.taskId = taskId


MAX_COMMAND_DISPLAY_LINES = 2
MAX_COMMAND_DISPLAY_CHARS = 160


def renderToolUseMessage(input_data: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Optional[str]:
    command = input_data.get("command")
    if not command:
        return None

    command = str(command)
    verbose = bool((options or {}).get("verbose"))

    sed_info = parseSedEditCommand(command)
    if sed_info:
        return sed_info.filePath if verbose else getDisplayPath(sed_info.filePath)

    if not verbose:
        label = extractBashCommentLabel(command)
        if label:
            if len(label) > MAX_COMMAND_DISPLAY_CHARS:
                return label[:MAX_COMMAND_DISPLAY_CHARS] + "..."
            return label

        lines = command.split("\n")
        truncated = command
        if len(lines) > MAX_COMMAND_DISPLAY_LINES:
            truncated = "\n".join(lines[:MAX_COMMAND_DISPLAY_LINES])
        if len(truncated) > MAX_COMMAND_DISPLAY_CHARS:
            truncated = truncated[:MAX_COMMAND_DISPLAY_CHARS]
        if truncated != command:
            return truncated.rstrip() + "..."

    return command


def renderToolResultMessage(result: Dict[str, Any], progressMessages=None, options: Optional[Dict[str, Any]] = None) -> str:
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")

    if result.get("isImage"):
        return "[Image data detected and sent to vivian]"
    if stdout != "":
        return str(stdout)
    if str(stderr).strip() != "":
        return str(stderr)
    if result.get("backgroundTaskId"):
        return "Running in the background"
    if result.get("interrupted"):
        return "Interrupted"
    interpretation = result.get("returnCodeInterpretation")
    if interpretation:
        return str(interpretation)
    return "(No output)"


def renderToolUseErrorMessage(error: str) -> str:
    return f"Bash error: {error}"


def renderToolUseProgressMessage(progressMessages=None, options: Optional[Dict[str, Any]] = None) -> str:
    return "Running..."


def renderToolUseQueuedMessage(command: Optional[str] = None) -> str:
    return "Waiting..."
