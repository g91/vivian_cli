"""NotebookEditTool UI — mirrors src/tools/NotebookEditTool/UI.tsx"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...utils.file import getDisplayPath


def getToolUseSummary(inputData: Optional[Dict[str, Any]]) -> Optional[str]:
    if not inputData:
        return None
    notebook_path = inputData.get("notebook_path") or inputData.get("filePath")
    if not notebook_path:
        return None
    return getDisplayPath(str(notebook_path))


def renderToolUseMessage(inputData: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Render the tool use message for NotebookEditTool."""
    notebook_path = inputData.get("notebook_path") or inputData.get("filePath")
    cell_id = inputData.get("cell_id")
    if not notebook_path or cell_id is None:
        return None

    notebook_path = str(notebook_path)
    display_path = notebook_path if bool((options or {}).get("verbose")) else getDisplayPath(notebook_path)
    return f"{display_path}@{cell_id}"


def renderToolResultMessage(output: Dict[str, Any]) -> Optional[str]:
    """Render the tool result message for NotebookEditTool."""
    if output.get("error"):
        return f"NotebookEdit error: {output['error']}"
    if output.get("success"):
        cell_id = output.get("cell_id")
        if cell_id is not None:
            return f"Updated cell {cell_id}"
        return "Updated notebook cell"
    return None

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for NotebookEditTool."""
    return f"NotebookEdit error: {errorMessage}"
