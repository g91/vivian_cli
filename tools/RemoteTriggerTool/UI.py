"""RemoteTriggerTool UI — mirrors src/tools/RemoteTriggerTool/UI.tsx"""
from typing import Any, Dict, Optional


def renderToolUseMessage(inputData: Dict[str, Any]) -> str:
    """Render the tool use message for RemoteTriggerTool."""
    action = str(inputData.get("action") or "")
    trigger_id = str(inputData.get("trigger_id") or "")
    return f"{action}{f' {trigger_id}' if trigger_id else ''}"

def renderToolResultMessage(output: Dict[str, Any]) -> Optional[str]:
    """Render the tool result message for RemoteTriggerTool."""
    if output.get("error"):
        return f"Remote trigger error: {output['error']}"

    status = output.get("status")
    json_text = str(output.get("json") or "")
    if status is None:
        return None

    lines = json_text.count("\n") + 1 if json_text else 1
    return f"HTTP {status} ({lines} lines)"

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for RemoteTriggerTool."""
    return f"Remote trigger error: {errorMessage}"
