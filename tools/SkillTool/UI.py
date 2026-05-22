"""SkillTool UI — mirrors src/tools/SkillTool/UI.tsx."""

from __future__ import annotations

from typing import Any, Dict, Optional


def renderToolUseMessage(inputData: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Render the tool use message for SkillTool."""
    del options
    skill = str(inputData.get("skill") or inputData.get("skill_name") or "")
    return skill or None


def renderToolResultMessage(output: Dict[str, Any]) -> Optional[str]:
    """Render the tool result message for SkillTool."""
    if output.get("error"):
        return f"Skill error: {output['error']}"
    if output.get("status") == "forked":
        return "Done"

    parts = ["Successfully loaded skill"]
    allowed_tools = output.get("allowed_tools")
    if isinstance(allowed_tools, list) and allowed_tools:
        count = len(allowed_tools)
        suffix = "tool" if count == 1 else "tools"
        parts.append(f"{count} {suffix} allowed")

    model = output.get("model")
    if model:
        parts.append(str(model))
    return " - ".join(parts)

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for SkillTool."""
    return f"Skill error: {errorMessage}"
