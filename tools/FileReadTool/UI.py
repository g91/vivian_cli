"""FileReadTool UI — mirrors src/tools/FileReadTool/UI.tsx"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...utils.file import getDisplayPath
from ...utils.task.diskOutput import getTaskOutputDir


def _get_agent_output_task_id(file_path: str) -> Optional[str]:
    prefix = getTaskOutputDir() + "/"
    suffix = ".output"
    if file_path.startswith(prefix) and file_path.endswith(suffix):
        task_id = file_path[len(prefix):-len(suffix)]
        if 0 < len(task_id) <= 20:
            return task_id
    return None


def userFacingName(inputData: Optional[Dict[str, Any]] = None) -> str:
    file_path = ""
    if inputData:
        file_path = str(inputData.get("file_path") or inputData.get("filePath") or "")
    if file_path and _get_agent_output_task_id(file_path):
        return "Read agent output"
    return "Read"


def renderToolUseMessage(inputData: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Render the tool use message for FileReadTool."""
    file_path = inputData.get("file_path") or inputData.get("filePath")
    if not file_path:
        return None

    file_path = str(file_path)
    if _get_agent_output_task_id(file_path):
        return ""

    verbose = bool((options or {}).get("verbose"))
    display_path = file_path if verbose else getDisplayPath(file_path)
    start_line = inputData.get("start_line", inputData.get("startLine"))
    end_line = inputData.get("end_line", inputData.get("endLine"))

    if verbose and start_line is not None and end_line is not None:
        return f"{display_path} · lines {start_line}-{end_line}"
    if verbose and start_line is not None:
        return f"{display_path} · from line {start_line}"
    return display_path


def renderToolUseTag(inputData: Dict[str, Any]) -> Optional[str]:
    file_path = inputData.get("file_path") or inputData.get("filePath")
    if not file_path:
        return None
    return _get_agent_output_task_id(str(file_path))


def renderToolResultMessage(output: Dict[str, Any]) -> Optional[str]:
    """Render the tool result message for FileReadTool."""
    if output.get("isImage"):
        return "Read image"

    content = output.get("content")
    if isinstance(content, str):
        num_lines = len(content.splitlines()) if content else 0
    else:
        num_lines = 0

    if num_lines == 0:
        stored_num_lines = output.get("numLines")
        if isinstance(stored_num_lines, int):
            num_lines = stored_num_lines

    noun = "line" if num_lines == 1 else "lines"
    return f"Read {num_lines} {noun}"


def getToolUseSummary(inputData: Optional[Dict[str, Any]]) -> Optional[str]:
    if not inputData:
        return None
    file_path = inputData.get("file_path") or inputData.get("filePath")
    if not file_path:
        return None

    file_path = str(file_path)
    task_id = _get_agent_output_task_id(file_path)
    if task_id:
        return task_id
    return getDisplayPath(file_path)

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for FileReadTool."""
    return f"Read error: {errorMessage}"
