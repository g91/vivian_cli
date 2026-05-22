"""TeamCreateTool UI — mirrors src/tools/TeamCreateTool/UI.tsx"""
from typing import Any, Dict, Optional

def renderToolUseMessage(inputData: Dict[str, Any]) -> str:
    """Render the tool use message for TeamCreateTool."""
    name = str(inputData.get("team_name") or inputData.get("name") or "")
    return f"create team: {name}"

def renderToolResultMessage(output: Dict[str, Any]) -> Optional[str]:
    """Render the tool result message for TeamCreateTool."""
    if output.get("success") is False:
        return str(output.get("message") or output.get("error") or "Team create error")

    team_name = output.get("team_name") or output.get("name")
    if team_name:
        return f'Created team "{team_name}"'
    return None

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for TeamCreateTool."""
    return f"Team create error: {errorMessage}"
