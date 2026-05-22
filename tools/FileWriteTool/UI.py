"""FileWriteTool UI — mirrors src/tools/FileWriteTool/UI.tsx"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...utils.file import getDisplayPath


def userFacingName() -> str:
    return "Write"


def getToolUseSummary(inputData: Optional[Dict[str, Any]]) -> Optional[str]:
    if not inputData:
        return None
    file_path = inputData.get("file_path") or inputData.get("filePath")
    if not file_path:
        return None
    return getDisplayPath(str(file_path))


def renderToolUseMessage(inputData: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Render the tool use message for FileWriteTool."""
    file_path = inputData.get("file_path") or inputData.get("filePath")
    if not file_path:
        return None
    file_path = str(file_path)
    if bool((options or {}).get("verbose")):
        return file_path
    return getDisplayPath(file_path)


def renderToolResultMessage(output: Dict[str, Any]) -> Optional[str]:
    """Render the tool result message for FileWriteTool."""
    file_path = output.get("filePath") or output.get("path")
    if not file_path:
        return None

    action = "Created" if output.get("isNewFile") else "Wrote"
    lines_added = output.get("linesAdded")
    if isinstance(lines_added, int):
        noun = "line" if lines_added == 1 else "lines"
        return f"{action} {lines_added} {noun} to {file_path}"
    return f"{action} {file_path}"

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for FileWriteTool."""
    return f"Write error: {errorMessage}"
