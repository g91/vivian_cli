"""GrepTool UI — mirrors src/tools/GrepTool/UI.tsx"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from ...utils.file import getDisplayPath


def userFacingName() -> str:
    return "Search"


def renderToolUseMessage(inputData: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Render the tool use message for GrepTool."""
    pattern = inputData.get("pattern")
    if not pattern:
        return None

    parts = [f'pattern: "{pattern}"']
    path = inputData.get("path")
    if path:
        verbose = bool((options or {}).get("verbose"))
        display_path = str(path) if verbose else getDisplayPath(str(path))
        parts.append(f'path: "{display_path}"')
    return ", ".join(parts)


def _match_file_path(match: Dict[str, Any]) -> Optional[str]:
    if not isinstance(match, dict):
        return None

    file_path = match.get("file")
    if isinstance(file_path, str) and file_path:
        return file_path

    data = match.get("data")
    if isinstance(data, dict):
        path = data.get("path")
        if isinstance(path, dict):
            text = path.get("text")
            if isinstance(text, str) and text:
                return text

    raw = match.get("raw")
    if isinstance(raw, str) and raw:
        return raw.split(":", 1)[0] or None

    return None


def renderToolResultMessage(output: Dict[str, Any], progressMessages=None, options: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Render the tool result message for GrepTool."""
    matches: List[Dict[str, Any]] = output.get("matches", [])
    num_matches = output.get("numMatches")
    if not isinstance(num_matches, int):
        num_matches = len(matches)

    if num_matches == 0:
        return "No matches found"

    unique_files: Set[str] = set()
    for match in matches:
        file_path = _match_file_path(match)
        if file_path:
            unique_files.add(file_path)

    noun = "match" if num_matches == 1 else "matches"
    summary = f"Found {num_matches} {noun}"
    if unique_files:
        file_noun = "file" if len(unique_files) == 1 else "files"
        summary += f" across {len(unique_files)} {file_noun}"
    if output.get("truncated"):
        summary += " (truncated)"

    if bool((options or {}).get("verbose")) and unique_files:
        file_list = "\n".join(sorted(unique_files))
        return f"{summary}\n{file_list}"
    return summary


def getToolUseSummary(inputData: Optional[Dict[str, Any]]) -> Optional[str]:
    if not inputData:
        return None
    pattern = inputData.get("pattern")
    return str(pattern) if pattern else None

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for GrepTool."""
    return f"Grep error: {errorMessage}"
