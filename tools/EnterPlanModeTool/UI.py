"""EnterPlanModeTool UI — mirrors src/tools/EnterPlanModeTool/UI.tsx"""
from typing import Any, Dict, Optional

def renderToolUseMessage() -> None:
    """Render the tool use message for EnterPlanModeTool."""
    return None

def renderToolResultMessage(output: Dict[str, Any]) -> Optional[str]:
    """Render the tool result message for EnterPlanModeTool."""
    if output.get("entered"):
        return "Entered plan mode"
    return None

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for EnterPlanModeTool."""
    return f"Plan mode error: {errorMessage}"
