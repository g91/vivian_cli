"""WebSearchTool UI — mirrors src/tools/WebSearchTool/UI.tsx."""

from __future__ import annotations

from typing import Any, Dict, Optional


def _get_search_summary(results: list[Any]) -> tuple[int, int]:
    search_count = 0
    total_result_count = 0
    for result in results:
        if isinstance(result, dict):
            search_count += 1
            content = result.get("content")
            if isinstance(content, list):
                total_result_count += len(content)
    return search_count, total_result_count


def renderToolUseMessage(inputData: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Render the tool use message for WebSearchTool."""
    query = str(inputData.get("query") or "")
    if not query:
        return None
    verbose = bool((options or {}).get("verbose", False))
    message = f'"{query}"'
    if verbose:
        allowed = inputData.get("allowed_domains") or []
        blocked = inputData.get("blocked_domains") or []
        if allowed:
            message += f", only allowing domains: {', '.join(str(v) for v in allowed)}"
        if blocked:
            message += f", blocking domains: {', '.join(str(v) for v in blocked)}"
    return message


def renderToolResultMessage(output: Dict[str, Any]) -> Optional[str]:
    """Render the tool result message for WebSearchTool."""
    results = output.get("results") or []
    search_count, _total_result_count = _get_search_summary(results if isinstance(results, list) else [])
    duration_seconds = float(output.get("durationSeconds") or 0.0)
    time_display = f"{round(duration_seconds)}s" if duration_seconds >= 1 else f"{round(duration_seconds * 1000)}ms"
    suffix = "es" if search_count != 1 else ""
    return f"Did {search_count} search{suffix} in {time_display}"


def getToolUseSummary(inputData: Optional[Dict[str, Any]]) -> Optional[str]:
    query = str((inputData or {}).get("query") or "")
    return query or None

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for WebSearchTool."""
    return f"Search error: {errorMessage}"
