"""GlobTool UI — mirrors src/tools/GlobTool/UI.tsx"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...utils.file import getDisplayPath


def userFacingName() -> str:
    return "Search"


def renderToolUseMessage(inputData: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Render the tool use message for GlobTool."""
    pattern = inputData.get("pattern")
    if not pattern:
        return None

    path = inputData.get("path")
    verbose = bool((options or {}).get("verbose"))
    if not path:
        return f'pattern: "{pattern}"'
    display_path = str(path) if verbose else getDisplayPath(str(path))
    return f'pattern: "{pattern}", path: "{display_path}"'


def renderToolResultMessage(output: Dict[str, Any]) -> Optional[str]:
    """Render the tool result message for GlobTool."""
    num_files = output.get("numFiles")
    files = output.get("files", [])
    if isinstance(num_files, int):
        if num_files == 0:
            return "No files found"
        suffix = " (truncated)" if output.get("truncated") else ""
        noun = "file" if num_files == 1 else "files"
        return f"Found {num_files} {noun}{suffix}"

    if not files:
        return "No files found"
    noun = "file" if len(files) == 1 else "files"
    return f"Found {len(files)} {noun}"


def getToolUseSummary(inputData: Optional[Dict[str, Any]]) -> Optional[str]:
    if not inputData:
        return None
    pattern = inputData.get("pattern")
    return str(pattern) if pattern else None

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for GlobTool."""
    return f"Glob error: {errorMessage}"
