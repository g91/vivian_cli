"""TaskCreateTool prompt — mirrors src/tools/TaskCreateTool/prompt.ts"""
TASK_CREATE_TOOL_NAME = "TaskCreate"

DESCRIPTION = "Create a new task"

TASK_CREATE_PROMPT = """Use this tool to create a new task for tracking work.
Tasks can be:
1. Independent work items
2. Sub-tasks of larger tasks
3. Scheduled for future execution

Each task has a title, description, status, and optional parent task."""
