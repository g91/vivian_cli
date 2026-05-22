"""EnterWorktreeTool — mirrors src/tools/EnterWorktreeTool/EnterWorktreeTool.tsx"""
from __future__ import annotations
from typing import Any, Dict

TOOL_NAME = "EnterWorktree"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["branch"],
    "properties": {
        "branch": {"type": "string", "description": "Branch name for the worktree"},
        "path": {"type": "string", "description": "Optional path for the worktree"},
    },
}


async def description() -> str:
    return "Create or switch to a git worktree for isolated work."


async def prompt() -> str:
    return "Use this tool to create a git worktree for isolated feature/fix work."


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    return {"entered": True, "branch": input_data.get("branch")}
