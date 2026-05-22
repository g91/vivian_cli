"""FileEditTool UI — mirrors src/tools/FileEditTool/UI.tsx"""
from __future__ import annotations
from typing import Any, Dict, Optional

from ...utils.file import getDisplayPath


def userFacingName(inputData: Optional[Dict[str, Any]] = None) -> str:
    if inputData and inputData.get("old_string", inputData.get("oldString")) == "":
        return "Create"
    return "Update"


def getToolUseSummary(inputData: Optional[Dict[str, Any]]) -> Optional[str]:
    if not inputData:
        return None
    file_path = inputData.get("file_path") or inputData.get("filePath")
    if not file_path:
        return None
    return getDisplayPath(str(file_path))


def renderToolUseMessage(input_data: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Optional[str]:
    file_path = input_data.get("file_path") or input_data.get("filePath")
    if not file_path:
        return None
    file_path = str(file_path)
    if bool((options or {}).get("verbose")):
        return file_path
    return getDisplayPath(file_path)


def renderToolResultMessage(result: Dict[str, Any]) -> str:
    if result.get("error"):
        return f"Error: {result['error']}"

    file_path = result.get("filePath", "")
    lines_added = result.get("linesAdded")
    lines_removed = result.get("linesRemoved")

    if isinstance(lines_added, int) and isinstance(lines_removed, int):
        parts = []
        if lines_added:
            parts.append(f"+{lines_added}")
        if lines_removed:
            parts.append(f"-{lines_removed}")
        if parts:
            return f"Updated {file_path} ({', '.join(parts)})"
    return f"Updated {file_path}"


def renderToolUseErrorMessage(error: str) -> str:
    return f"Edit error: {error}"
