"""FileWriteTool — mirrors src/tools/FileWriteTool/FileWriteTool.tsx"""
from __future__ import annotations
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from ...utils.commitAttribution import getFileMtime, stateToSnapshotMessage, trackFileModification
from ...utils.fileHistory import fileHistoryTrackEdit
from ...utils.sessionStorage import recordAttributionSnapshot

logger = logging.getLogger(__name__)

TOOL_NAME = "Write"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["file_path", "content"],
    "properties": {
        "file_path": {
            "type": "string",
            "description": "Absolute path to the file to create or overwrite",
        },
        "content": {
            "type": "string",
            "description": "The content to write to the file",
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "filePath": {"type": "string"},
        "isNewFile": {"type": "boolean"},
    },
}


async def description() -> str:
    return "Create or overwrite a file with the given content."


async def prompt() -> str:
    return (
        "Use this tool to create new files or completely overwrite existing ones. "
        "For making targeted changes to existing files, prefer Edit instead. "
        "Always use absolute paths. Creates parent directories automatically."
    )


def userFacingName() -> str:
    return ""


def getToolUseSummary(input_data: Dict[str, Any]) -> str:
    return input_data.get("file_path", "")


def getActivityDescription(input_data: Dict[str, Any]) -> str:
    return f"Writing {Path(input_data.get('file_path', '')).name}"


def _get_cwd(context: Any) -> Path:
    """Return the current working directory from context or os.getcwd()."""
    if isinstance(context, dict) and context.get("cwd"):
        return Path(context["cwd"]).resolve()
    return Path(os.getcwd()).resolve()


def _resolve_path(file_path: str, context: Any) -> Path:
    """Expand ~ and resolve relative paths against context cwd."""
    p = Path(file_path).expanduser()
    if not p.is_absolute():
        p = _get_cwd(context) / p
    return p.resolve()


def _sandbox_path(path: Path, cwd: Path) -> tuple[Path, bool]:
    """Ensure path is inside cwd. If not, redirect to cwd/filename.
    
    Returns (final_path, was_redirected).
    """
    try:
        path.relative_to(cwd)
        return path, False
    except ValueError:
        # Path is outside cwd — redirect to cwd/filename only
        return cwd / path.name, True


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    # Accept common parameter name variations that models use
    filePath = (
        input_data.get("file_path")
        or input_data.get("path")
        or input_data.get("filepath")
        or input_data.get("filename")
        or input_data.get("file")
        or ""
    )
    content = (
        input_data.get("content")
        or input_data.get("text")
        or input_data.get("body")
        or input_data.get("data")
        or ""
    )

    if not filePath:
        return {"error": "file_path is required"}

    cwd = _get_cwd(context)
    path = _resolve_path(filePath, context)

    # If the model passed a bare directory (forgot the filename), use filename from input
    if path.is_dir():
        # Try to pull a sensible filename from the raw input
        raw_name = Path(filePath).name
        path = cwd / (raw_name if raw_name else "output.txt")

    # Sandbox: if path is outside cwd, redirect to cwd/filename
    path, redirected = _sandbox_path(path, cwd)
    if redirected:
        logger.warning(
            "[write] path '%s' is outside cwd, redirected to %s", filePath, path
        )

    isNewFile = not path.exists()
    old_content = path.read_text(encoding="utf-8", errors="replace") if not isNewFile else ""
    old_lines = path.read_text(encoding="utf-8", errors="replace").count("\n") + 1 if not isNewFile else 0

    try:
        if isinstance(context, dict) and context.get("update_file_history_state") and context.get("file_history_message_id"):
            await fileHistoryTrackEdit(
                context["update_file_history_state"],
                (str(path), context["file_history_message_id"]),
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if isinstance(context, dict) and context.get("update_attribution_state") and context.get("attribution_message_id"):
            mtime = await getFileMtime(str(path))
            current_holder = {"state": None}
            context["update_attribution_state"](
                lambda state: _capture_attribution_state(
                    trackFileModification(state, str(path), old_content, content, False, mtime),
                    current_holder,
                )
            )
            current_state = current_holder.get("state")
            if isinstance(current_state, dict):
                recordAttributionSnapshot(stateToSnapshotMessage(current_state, context["attribution_message_id"]))
        new_lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        return {
            "filePath": str(path),
            "isNewFile": isNewFile,
            "linesAdded": new_lines if isNewFile else max(0, new_lines - old_lines),
            "linesRemoved": 0 if isNewFile else max(0, old_lines - new_lines),
        }
    except OSError as e:
        return {"error": str(e)}


def _capture_attribution_state(state: Dict[str, Any], holder: Dict[str, Any]) -> Dict[str, Any]:
    holder["state"] = state
    return state
