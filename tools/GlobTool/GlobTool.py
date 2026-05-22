"""GlobTool — mirrors src/tools/GlobTool/GlobTool.tsx"""
from __future__ import annotations
import glob
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

TOOL_NAME = "Glob"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["pattern"],
    "properties": {
        "pattern": {
            "type": "string",
            "description": "Glob pattern to search for (e.g. **/*.ts)",
        },
        "path": {
            "type": "string",
            "description": "Directory to search in (defaults to cwd)",
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "files": {"type": "array", "items": {"type": "string"}},
        "numFiles": {"type": "integer"},
        "truncated": {"type": "boolean"},
    },
}

MAX_RESULTS = 1000


async def description() -> str:
    return "Find files matching a glob pattern."


async def prompt() -> str:
    return (
        "Use this tool to find files by glob pattern. "
        "Returns a list of matching file paths. "
        "Use ** for recursive matching, * for single-level wildcards. "
        "Results are sorted by modification time (newest first)."
    )


def userFacingName() -> str:
    return ""


def getToolUseSummary(input_data: Dict[str, Any]) -> str:
    return input_data.get("pattern", "")


def getActivityDescription(input_data: Dict[str, Any]) -> str:
    return f"Searching for {input_data.get('pattern', '')}"


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    pattern = (
        input_data.get("pattern")
        or input_data.get("glob")
        or input_data.get("match")
        or ""
    )
    searchPath = (
        input_data.get("path")
        or input_data.get("directory")
        or input_data.get("dir")
        or input_data.get("folder")
        or None
    )

    if not searchPath and isinstance(context, dict):
        searchPath = context.get("cwd")
    if not searchPath:
        searchPath = os.getcwd()

    # Resolve relative paths against cwd
    if not os.path.isabs(searchPath):
        cwd = context.get("cwd", os.getcwd()) if isinstance(context, dict) else os.getcwd()
        searchPath = str(Path(cwd) / searchPath)

    # Run glob
    try:
        fullPattern = os.path.join(searchPath, pattern)
        matches = glob.glob(fullPattern, recursive=True)
        # Sort by mtime (newest first)
        try:
            matches.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        except OSError:
            matches.sort()

        truncated = len(matches) > MAX_RESULTS
        matches = matches[:MAX_RESULTS]

        return {
            "files": matches,
            "numFiles": len(matches),
            "truncated": truncated,
        }
    except Exception as e:
        return {"error": str(e), "files": [], "numFiles": 0}
