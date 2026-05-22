"""SleepTool prompt — mirrors src/tools/SleepTool/prompt.ts"""
SLEEP_TOOL_NAME = "Sleep"

DESCRIPTION = "Pause execution for a specified duration"

SLEEP_PROMPT = """Use this tool to pause execution for a specified duration.
This is useful for:
1. Waiting for external processes to complete
2. Rate limiting API calls
3. Spacing out operations

Duration is specified in seconds (minimum 1, maximum 300)."""
