"""TaskListTool prompt — mirrors src/tools/TaskListTool/prompt.ts"""
TASK_LIST_TOOL_NAME = "TaskList"

DESCRIPTION = "List all tasks"

TASK_LIST_PROMPT = """Use this tool to list all tasks. You can filter by:
1. Status (pending, in-progress, completed, failed)
2. Parent task ID
3. Creation date range

Results are sorted by creation time (newest first)."""
