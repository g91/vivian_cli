"""TaskStopTool prompt — mirrors src/tools/TaskStopTool/prompt.ts"""
TASK_STOP_TOOL_NAME = "TaskStop"

DESCRIPTION = "Stop a running task"

TASK_STOP_PROMPT = """Use this tool to stop a running task.
The task will be marked as cancelled and any in-progress work will be halted.
You cannot stop tasks that are already completed or cancelled."""
