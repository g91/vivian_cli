"""TaskUpdateTool prompt — mirrors src/tools/TaskUpdateTool/prompt.ts"""
TASK_UPDATE_TOOL_NAME = "TaskUpdate"

DESCRIPTION = "Update a task's status or details"

TASK_UPDATE_PROMPT = """Use this tool to update a task. You can change:
1. Status (pending, in-progress, completed, failed, cancelled)
2. Title and description
3. Parent task
4. Priority

Only the fields you specify will be updated."""
