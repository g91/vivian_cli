"""WebFetchTool UI — mirrors src/tools/WebFetchTool/UI.tsx."""

from __future__ import annotations

from typing import Any, Dict, Optional


def _format_file_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    size = float(max(0, num_bytes))
    unit = units[0]
    for candidate in units:
        unit = candidate
        if size < 1024 or candidate == units[-1]:
            break
        size /= 1024.0
    if unit == "B":
        return f"{int(size)} {unit}"
    return f"{size:.1f} {unit}"


def renderToolUseMessage(inputData: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Render the tool use message for WebFetchTool."""
    url = str(inputData.get("url") or "")
    if not url:
        return None
    prompt = str(inputData.get("prompt") or "")
    verbose = bool((options or {}).get("verbose", False))
    if verbose:
        suffix = f', prompt: "{prompt}"' if prompt else ""
        return f'url: "{url}"{suffix}'
    return url


def renderToolUseProgressMessage() -> str:
    return "Fetching..."


def renderToolResultMessage(
    output: Dict[str, Any],
    progressMessages: Optional[list[Any]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Render the tool result message for WebFetchTool."""
    del progressMessages
    if output.get("error"):
        return f"Fetch error: {output['error']}"
    formatted_size = _format_file_size(int(output.get("bytes") or 0))
    code = output.get("code", 0)
    code_text = output.get("codeText", "")
    summary = f"Received {formatted_size} ({code} {code_text})"
    verbose = bool((options or {}).get("verbose", False))
    if not verbose:
        return summary
    result = str(output.get("result") or "")
    return f"{summary}\n{result}" if result else summary


def getToolUseSummary(inputData: Optional[Dict[str, Any]]) -> Optional[str]:
    url = str((inputData or {}).get("url") or "")
    return url or None

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for WebFetchTool."""
    return f"Fetch error: {errorMessage}"
