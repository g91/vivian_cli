"""TaskStopTool UI — mirrors src/tools/TaskStopTool/UI.tsx"""
from typing import Any, Dict, Optional

_MAX_COMMAND_DISPLAY_LINES = 2
_MAX_COMMAND_DISPLAY_CHARS = 160


def _truncate_command(command: str) -> str:
    lines = command.split("\n")
    truncated = command
    if len(lines) > _MAX_COMMAND_DISPLAY_LINES:
        truncated = "\n".join(lines[:_MAX_COMMAND_DISPLAY_LINES])
    if len(truncated) > _MAX_COMMAND_DISPLAY_CHARS:
        truncated = truncated[:_MAX_COMMAND_DISPLAY_CHARS]
    return truncated.strip()

def renderToolUseMessage(inputData: Dict[str, Any]) -> str:
    """Render the tool use message for TaskStopTool."""
    del inputData
    return ""

def renderToolResultMessage(output: Dict[str, Any], progressMessages: Optional[list[Any]] = None, options: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Render the tool result message for TaskStopTool."""
    del progressMessages
    if output.get("error"):
        return f"Stop task error: {output['error']}"

    raw_command = str(output.get("command") or "")
    if not raw_command:
        return output.get("message")

    verbose = bool((options or {}).get("verbose"))
    command = raw_command if verbose else _truncate_command(raw_command)
    suffix = "… · stopped" if command != raw_command else " · stopped"
    return f"{command}{suffix}"

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for TaskStopTool."""
    return f"Stop task error: {errorMessage}"
