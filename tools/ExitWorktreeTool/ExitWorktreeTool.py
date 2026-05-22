"""ExitWorktreeTool — mirrors src/tools/ExitWorktreeTool/ExitWorktreeTool.tsx"""
from __future__ import annotations
from typing import Any, Dict

TOOL_NAME = "ExitWorktree"

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "merge": {"type": "boolean", "description": "Whether to merge the worktree branch"},
    },
}


async def description() -> str:
    return "Exit the current git worktree."


async def prompt() -> str:
    return "Use this tool to exit the current git worktree and return to the main working tree."


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    return {"exited": True}
