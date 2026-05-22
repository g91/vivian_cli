"""TodoWriteTool — mirrors src/tools/TodoWriteTool/TodoWriteTool.tsx"""
from __future__ import annotations
from typing import Any, Dict, List

TOOL_NAME = "TodoWrite"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["todos"],
    "properties": {
        "todos": {
            "type": "array",
            "description": "Complete list of todos replacing the existing list",
            "items": {
                "type": "object",
                "required": ["id", "content", "status", "priority"],
                "properties": {
                    "id": {"type": "string"},
                    "content": {"type": "string"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                },
            },
        },
    },
}


async def description() -> str:
    return "Write or update the todo list for the current session."


async def prompt() -> str:
    return (
        "Use this tool to create and manage a todo list for tracking progress on complex tasks. "
        "Always provide the COMPLETE list of todos — this replaces the existing list entirely. "
        "Mark items in_progress when starting them, completed when done."
    )


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    todos = input_data.get("todos", [])
    if isinstance(context, dict) and "todo_list" in context:
        context["todo_list"] = todos
    return {"todos": todos, "count": len(todos)}
