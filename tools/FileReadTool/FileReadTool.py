"""FileReadTool — mirrors src/tools/FileReadTool/FileReadTool.tsx"""
from __future__ import annotations
import base64
import os
from pathlib import Path
from typing import Any, Dict, Optional

TOOL_NAME = "Read"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["file_path"],
    "properties": {
        "file_path": {
            "type": "string",
            "description": "Absolute path to the file to read",
        },
        "start_line": {
            "type": "integer",
            "description": "Optional start line (1-indexed, inclusive)",
        },
        "end_line": {
            "type": "integer",
            "description": "Optional end line (1-indexed, inclusive)",
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "content": {"type": "string"},
        "filePath": {"type": "string"},
        "numLines": {"type": "integer"},
        "startLine": {"type": "integer"},
        "endLine": {"type": "integer"},
        "isImage": {"type": "boolean"},
    },
}

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".bmp"}
_IMAGE_MIMETYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".bmp": "image/bmp",
}


async def description() -> str:
    return "Read the contents of a file (text or image)."


async def prompt() -> str:
    return (
        "Use this tool to read a file's contents. "
        "Specify start_line and end_line for large files to read a specific section. "
        "For images, the image content is returned directly. "
        "Always use absolute paths."
    )


def userFacingName() -> str:
    return ""


def getToolUseSummary(input_data: Dict[str, Any]) -> str:
    return input_data.get("file_path", "")


def getActivityDescription(input_data: Dict[str, Any]) -> str:
    return f"Reading {Path(input_data.get('file_path', '')).name}"


def _resolve_path(file_path: str, context: Any) -> Path:
    """Expand ~ and resolve relative paths against context cwd."""
    p = Path(file_path).expanduser()
    if not p.is_absolute():
        cwd = context.get("cwd", os.getcwd()) if isinstance(context, dict) else os.getcwd()
        p = Path(cwd) / p
    return p.resolve()


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    filePath = (
        input_data.get("file_path")
        or input_data.get("path")
        or input_data.get("filepath")
        or input_data.get("filename")
        or input_data.get("file")
        or ""
    )
    startLine: Optional[int] = input_data.get("start_line") or input_data.get("startLine")
    endLine: Optional[int] = input_data.get("end_line") or input_data.get("endLine")

    path = _resolve_path(filePath, context)
    if not path.exists():
        return {"error": f"File not found: {path}"}

    suffix = path.suffix.lower()

    # Handle images
    if suffix in _IMAGE_EXTENSIONS:
        try:
            data = path.read_bytes()
            b64 = base64.b64encode(data).decode("ascii")
            mimeType = _IMAGE_MIMETYPES.get(suffix, "image/png")
            return {
                "filePath": str(path),
                "isImage": True,
                "imageData": b64,
                "mimeType": mimeType,
            }
        except OSError as e:
            return {"error": str(e)}

    # Text file
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"error": str(e)}

    lines = content.splitlines(keepends=True)
    numLines = len(lines)

    # Apply line range if requested
    if startLine is not None or endLine is not None:
        start0 = (startLine - 1) if startLine else 0
        end0 = endLine if endLine else numLines
        start0 = max(0, min(start0, numLines))
        end0 = max(0, min(end0, numLines))
        lines = lines[start0:end0]
        content = "".join(lines)

    return {
        "content": content,
        "filePath": filePath,
        "numLines": numLines,
        "startLine": startLine or 1,
        "endLine": endLine or numLines,
        "isImage": False,
    }
