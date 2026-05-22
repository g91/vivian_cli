"""ExitPlanModeTool UI — mirrors src/tools/ExitPlanModeTool/UI.tsx."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...utils.file import getDisplayPath
from ...utils.plans import getPlan


def renderToolUseMessage(_inputData: Optional[Dict[str, Any]] = None) -> None:
    """ExitPlanMode does not render a separate tool-use line in the Python UI."""
    return None


def renderToolResultMessage(
    output: Dict[str, Any],
    _progressMessagesForMessage: Optional[list[Any]] = None,
    _options: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Render the result summary for a completed ExitPlanMode call."""
    plan = str(output.get("plan") or "")
    file_path = output.get("filePath")
    is_empty = not plan.strip()
    display_path = getDisplayPath(str(file_path)) if file_path else ""

    if is_empty:
        return "Exited plan mode"

    if output.get("awaitingLeaderApproval"):
        lines = ["Plan submitted for team lead approval"]
        if display_path:
            lines.append(f"Plan file: {display_path}")
        lines.append("Waiting for team lead to review and approve...")
        return "\n".join(lines)

    lines = ["User approved vivian's plan"]
    if display_path:
        lines.append(f"Plan saved to: {display_path} · /plan to edit")
    lines.append("")
    lines.append(plan)
    return "\n".join(lines)


def renderToolUseRejectedMessage(
    inputData: Optional[Dict[str, Any]] = None,
    _options: Optional[Dict[str, Any]] = None,
) -> str:
    """Render the rejected-plan view shown when the user rejects the plan."""
    plan_content = None
    if isinstance(inputData, dict):
        raw_plan = inputData.get("plan")
        if isinstance(raw_plan, str) and raw_plan:
            plan_content = raw_plan
    if not plan_content:
        plan_content = getPlan() or "No plan found"
    return f"Plan needs revision:\n\n{plan_content}"


def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for ExitPlanModeTool."""
    return f"Exit plan mode error: {errorMessage}"
