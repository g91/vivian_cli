"""PowerShellTool UI — mirrors src/tools/PowerShellTool/UI.tsx"""

from __future__ import annotations

from typing import Any, Dict, Optional

MAX_COMMAND_DISPLAY_LINES = 2
MAX_COMMAND_DISPLAY_CHARS = 160


def renderToolUseMessage(inputData: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Render the tool use message for PowerShellTool."""
    command = inputData.get("command")
    if not command:
        return None

    command = str(command)
    if bool((options or {}).get("verbose")):
        return command

    lines = command.split("\n")
    truncated = command
    if len(lines) > MAX_COMMAND_DISPLAY_LINES:
        truncated = "\n".join(lines[:MAX_COMMAND_DISPLAY_LINES])
    if len(truncated) > MAX_COMMAND_DISPLAY_CHARS:
        truncated = truncated[:MAX_COMMAND_DISPLAY_CHARS]
    if truncated != command:
        return truncated.rstrip() + "..."
    return truncated


def renderToolUseProgressMessage(progressMessages=None, options: Optional[Dict[str, Any]] = None) -> str:
    return "Running..."


def renderToolUseQueuedMessage() -> str:
    return "Waiting..."


def renderToolResultMessage(output: Dict[str, Any], progressMessages=None, options: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Render the tool result message for PowerShellTool."""
    if output.get("isImage"):
        return "[Image data detected and sent to vivian]"

    stdout = str(output.get("stdout", ""))
    stderr = str(output.get("stderr", ""))
    if stdout:
        return stdout
    if stderr.strip():
        return stderr
    if output.get("backgroundTaskId"):
        return "Running in the background"
    if output.get("interrupted"):
        return "Interrupted"
    interpretation = output.get("returnCodeInterpretation")
    if interpretation:
        return str(interpretation)
    exit_code = output.get("exitCode")
    if isinstance(exit_code, int) and exit_code != 0:
        return f"Exit code: {exit_code}"
    return "(No output)"

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for PowerShellTool."""
    return f"PowerShell error: {errorMessage}"
