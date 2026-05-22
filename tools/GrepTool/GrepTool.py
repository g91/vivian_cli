"""GrepTool — mirrors src/tools/GrepTool/GrepTool.tsx"""
from __future__ import annotations
import asyncio
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

TOOL_NAME = "Grep"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["pattern"],
    "properties": {
        "pattern": {
            "type": "string",
            "description": "Regular expression pattern to search for",
        },
        "path": {
            "type": "string",
            "description": "Path to search in (file or directory)",
        },
        "include": {
            "type": "string",
            "description": "File glob pattern to include (e.g. *.ts)",
        },
        "exclude": {
            "type": "string",
            "description": "File glob pattern to exclude",
        },
        "-l": {
            "type": "boolean",
            "description": "Only print filenames with matches",
        },
        "-i": {
            "type": "boolean",
            "description": "Case-insensitive matching",
        },
        "-n": {
            "type": "boolean",
            "description": "Print line numbers",
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "matches": {"type": "array"},
        "numMatches": {"type": "integer"},
        "truncated": {"type": "boolean"},
    },
}

MAX_RESULTS = 1000


async def description() -> str:
    return "Search for text patterns using ripgrep or grep."


async def prompt() -> str:
    return (
        "Use this tool to search for text content using regular expressions. "
        "Searches files recursively by default. "
        "Specify `include` to filter by file type (e.g., *.py). "
        "Returns file paths and matching lines."
    )


def userFacingName() -> str:
    return ""


def getToolUseSummary(input_data: Dict[str, Any]) -> str:
    pattern = input_data.get("pattern", "")
    path = input_data.get("path", "")
    return f"{pattern} in {path}" if path else pattern


def getActivityDescription(input_data: Dict[str, Any]) -> str:
    return f"Searching for {input_data.get('pattern', '')}"


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    pattern = (
        input_data.get("pattern")
        or input_data.get("query")
        or input_data.get("search")
        or input_data.get("regex")
        or input_data.get("text")
        or ""
    )
    searchPath = (
        input_data.get("path")
        or input_data.get("directory")
        or input_data.get("dir")
        or input_data.get("folder")
        or ""
    )
    include = input_data.get("include") or input_data.get("include_pattern")
    exclude = input_data.get("exclude") or input_data.get("exclude_pattern")
    listOnly = input_data.get("-l", False) or input_data.get("list_only", False)
    caseInsensitive = input_data.get("-i", False) or input_data.get("case_insensitive", False)
    showLineNumbers = input_data.get("-n", True) or input_data.get("line_numbers", True)

    if not searchPath and isinstance(context, dict):
        searchPath = context.get("cwd", os.getcwd())
    if not searchPath:
        searchPath = os.getcwd()

    # Resolve relative paths against cwd
    if not os.path.isabs(searchPath):
        cwd = context.get("cwd", os.getcwd()) if isinstance(context, dict) else os.getcwd()
        searchPath = str(Path(cwd) / searchPath)

    # Try ripgrep first, fall back to grep
    rg_path = _find_rg()

    try:
        if rg_path:
            return await _run_rg(rg_path, pattern, searchPath, include, exclude, listOnly, caseInsensitive, showLineNumbers)
        else:
            return await _run_grep(pattern, searchPath, include, listOnly, caseInsensitive, showLineNumbers)
    except Exception as e:
        return {"error": str(e), "matches": [], "numMatches": 0}


def _find_rg() -> Optional[str]:
    """Find the ripgrep binary."""
    import shutil
    rg = shutil.which("rg")
    if rg:
        return rg
    # VS Code bundles ripgrep
    vscode_rg = os.environ.get("VSCODE_RIPGREP_PATH") or         "/snap/code-insiders/current/usr/share/code-insiders/resources/app/node_modules/@vscode/ripgrep/bin/rg"
    if os.path.exists(str(vscode_rg)):
        return str(vscode_rg)
    return None


async def _run_rg(
    rg_path: str,
    pattern: str,
    path: str,
    include: Optional[str],
    exclude: Optional[str],
    listOnly: bool,
    caseInsensitive: bool,
    showLineNumbers: bool,
) -> Dict[str, Any]:
    cmd = [rg_path, "--json", pattern, path]
    if caseInsensitive:
        cmd.append("-i")
    if include:
        cmd.extend(["--glob", include])
    if exclude:
        cmd.extend(["--glob", f"!{exclude}"])
    if listOnly:
        cmd.append("-l")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
    stdout = stdout_bytes.decode("utf-8", errors="replace")

    import json
    matches = []
    for line in stdout.splitlines():
        try:
            obj = json.loads(line)
            if obj.get("type") == "match":
                matches.append(obj)
        except json.JSONDecodeError:
            continue

    truncated = len(matches) > MAX_RESULTS
    return {
        "matches": matches[:MAX_RESULTS],
        "numMatches": len(matches),
        "truncated": truncated,
    }


async def _run_grep(
    pattern: str,
    path: str,
    include: Optional[str],
    listOnly: bool,
    caseInsensitive: bool,
    showLineNumbers: bool,
) -> Dict[str, Any]:
    cmd = ["grep", "-r", "--include={}".format(include or "*")]
    if caseInsensitive:
        cmd.append("-i")
    if listOnly:
        cmd.append("-l")
    if showLineNumbers and not listOnly:
        cmd.append("-n")
    cmd.extend(["-E", pattern, path])

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
    lines = stdout_bytes.decode("utf-8", errors="replace").splitlines()

    matches = [{"raw": line} for line in lines if line]
    truncated = len(matches) > MAX_RESULTS

    return {
        "matches": matches[:MAX_RESULTS],
        "numMatches": len(matches),
        "truncated": truncated,
    }
