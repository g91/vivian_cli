"""EnterPlanModeTool — mirrors src/tools/EnterPlanModeTool/EnterPlanModeTool.tsx"""
from __future__ import annotations
from typing import Any, Dict

TOOL_NAME = "EnterPlanMode"

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "plan": {"type": "string", "description": "Initial plan description (optional)"},
    },
}


async def description() -> str:
    return "Enter plan mode to draft and refine a plan before executing it."


async def prompt() -> str:
    return (
        "Use this tool to enter plan mode. In plan mode you can draft a plan, "
        "ask clarifying questions with AskUserQuestion, and refine your approach "
        "before executing any code changes. Exit plan mode with ExitPlanMode when ready."
    )


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    return {"entered": True, "plan": input_data.get("plan", "")}
