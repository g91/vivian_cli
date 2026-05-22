"""FileEditTool — mirrors src/tools/FileEditTool/FileEditTool.tsx"""
from __future__ import annotations
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...utils.commitAttribution import getFileMtime, stateToSnapshotMessage, trackFileModification
from ...utils.fileHistory import fileHistoryTrackEdit
from ...utils.sessionStorage import recordAttributionSnapshot
from .constants import FILE_EDIT_TOOL_NAME
from .editFile import FileEditError, applyEdit, editFile
from .prompt import DESCRIPTION, PROMPT

logger = logging.getLogger(__name__)

TOOL_NAME = FILE_EDIT_TOOL_NAME

INPUT_SCHEMA = {
    "type": "object",
    "required": ["file_path", "old_string", "new_string"],
    "properties": {
        "file_path": {
            "type": "string",
            "description": "Absolute path to the file to edit",
        },
        "old_string": {
            "type": "string",
            "description": "Exact string to find in the file",
        },
        "new_string": {
            "type": "string",
            "description": "Text to replace the old_string with",
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "filePath": {"type": "string"},
        "content": {"type": "string"},
        "structuredPatch": {"type": "string"},
    },
}


async def description() -> str:
    return DESCRIPTION


async def prompt() -> str:
    return PROMPT


def userFacingName() -> str:
    return ""


def getToolUseSummary(input_data: Dict[str, Any]) -> str:
    return input_data.get("file_path", "")


def getActivityDescription(input_data: Dict[str, Any]) -> str:
    return f"Editing {Path(input_data.get('file_path', '')).name}"


def _get_cwd(context: Any) -> Path:
    if isinstance(context, dict) and context.get("cwd"):
        return Path(context["cwd"]).resolve()
    return Path(os.getcwd()).resolve()


def _resolve_path(file_path: str, context: Any) -> str:
    """Expand ~ and resolve relative paths against context cwd."""
    p = Path(file_path).expanduser()
    if not p.is_absolute():
        p = _get_cwd(context) / p
    return str(p.resolve())


def _sandbox_to_cwd(path_str: str, context: Any) -> str:
    """If path is outside cwd, redirect to cwd/filename."""
    cwd = _get_cwd(context)
    p = Path(path_str)
    try:
        p.relative_to(cwd)
        return path_str
    except ValueError:
        redirected = str(cwd / p.name)
        logger.warning("[edit] path '%s' is outside cwd, redirected to %s", path_str, redirected)
        return redirected


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    rawPath = (
        input_data.get("file_path")
        or input_data.get("path")
        or input_data.get("filepath")
        or input_data.get("filename")
        or input_data.get("file")
        or ""
    )
    filePath = _sandbox_to_cwd(_resolve_path(rawPath, context), context)
    oldString = input_data.get("old_string") or input_data.get("oldString") or input_data.get("old") or ""
    newString = input_data.get("new_string") or input_data.get("newString") or input_data.get("new") or ""

    try:
        old_content = Path(filePath).read_text(encoding="utf-8", errors="replace") if Path(filePath).exists() else ""
        if isinstance(context, dict) and context.get("update_file_history_state") and context.get("file_history_message_id"):
            await fileHistoryTrackEdit(
                context["update_file_history_state"],
                (filePath, context["file_history_message_id"]),
            )
        newContent = editFile(filePath, oldString, newString)
        if isinstance(context, dict) and context.get("update_attribution_state") and context.get("attribution_message_id"):
            mtime = await getFileMtime(filePath)
            current_holder = {"state": None}
            context["update_attribution_state"](
                lambda state: _capture_attribution_state(
                    trackFileModification(state, filePath, old_content, newContent, False, mtime),
                    current_holder,
                )
            )
            current_state = current_holder.get("state")
            if isinstance(current_state, dict):
                recordAttributionSnapshot(stateToSnapshotMessage(current_state, context["attribution_message_id"]))
        lines_added = newString.count("\n") + (1 if newString and not newString.endswith("\n") else 0)
        lines_removed = oldString.count("\n") + (1 if oldString and not oldString.endswith("\n") else 0)
        return {
            "filePath": filePath,
            "content": newContent,
            "linesAdded": max(0, lines_added - lines_removed),
            "linesRemoved": max(0, lines_removed - lines_added),
        }
    except FileEditError as e:
        return {
            "error": str(e),
            "errorCode": e.code,
        }


def _capture_attribution_state(state: Dict[str, Any], holder: Dict[str, Any]) -> Dict[str, Any]:
    holder["state"] = state
    return state
