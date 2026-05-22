"""TeamDeleteTool UI — mirrors src/tools/TeamDeleteTool/UI.tsx"""
from typing import Any, Dict, Optional

def renderToolUseMessage(inputData: Dict[str, Any]) -> str:
    """Render the tool use message for TeamDeleteTool."""
    del inputData
    return "cleanup team: current"

def renderToolResultMessage(output: Dict[str, Any]) -> Optional[str]:
    """Render the tool result message for TeamDeleteTool."""
    del output
    return None

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for TeamDeleteTool."""
    return f"Team delete error: {errorMessage}"
