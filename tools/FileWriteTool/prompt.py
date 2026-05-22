"""FileWriteTool prompt — mirrors src/tools/FileWriteTool/prompt.ts"""
FILE_WRITE_TOOL_NAME = "Write"

DESCRIPTION = "Write content to a file, creating it if it doesn't exist"

FILE_WRITE_PROMPT = """Use this tool to write content to a file. This will:
1. Create parent directories if they don't exist
2. Create the file if it doesn't exist
3. Overwrite the file if it already exists

Use FileEditTool for partial edits to existing files instead."""
