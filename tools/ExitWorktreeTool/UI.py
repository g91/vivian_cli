"""ExitWorktreeTool UI — mirrors src/tools/ExitWorktreeTool/UI.tsx"""
from typing import Any, Dict, Optional

def renderToolUseMessage() -> str:
    """Render the tool use message for ExitWorktreeTool."""
    return "Exiting worktree..."

def renderToolResultMessage(output: Dict[str, Any]) -> Optional[str]:
    """Render the tool result message for ExitWorktreeTool."""
    action = output.get("action")
    branch = output.get("worktreeBranch") or output.get("branch")
    original_cwd = output.get("originalCwd") or output.get("path")

    if action == "keep":
        label = "Kept worktree"
    elif action:
        label = "Removed worktree"
    elif output.get("exited"):
        label = "Exited worktree"
    else:
        return None

    first_line = label
    if branch:
        first_line += f" (branch {branch})"
    if original_cwd:
        return f"{first_line}\nReturned to {original_cwd}"
    return first_line

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for ExitWorktreeTool."""
    return f"Exit worktree error: {errorMessage}"
