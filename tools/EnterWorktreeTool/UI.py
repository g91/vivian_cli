"""EnterWorktreeTool UI — mirrors src/tools/EnterWorktreeTool/UI.tsx"""
from typing import Any, Dict, Optional

def renderToolUseMessage(inputData: Dict[str, Any]) -> str:
    """Render the tool use message for EnterWorktreeTool."""
    del inputData
    return "Creating worktree..."

def renderToolResultMessage(output: Dict[str, Any]) -> Optional[str]:
    """Render the tool result message for EnterWorktreeTool."""
    branch = output.get("worktreeBranch") or output.get("branch")
    path = output.get("worktreePath") or output.get("path")
    if not branch and not path:
        return None
    if path:
        if branch:
            return f"Switched to worktree on branch {branch}\n{path}"
        return str(path)
    return f"Switched to worktree on branch {branch}"

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for EnterWorktreeTool."""
    return f"Worktree error: {errorMessage}"
