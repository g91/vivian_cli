"""FileReadTool prompt — mirrors src/tools/FileReadTool/prompt.ts"""
FILE_READ_TOOL_NAME = "Read"

FILE_UNCHANGED_STUB = (
	"File unchanged since last read. The content from the earlier Read tool_result in this "
	"conversation is still current - refer to that instead of re-reading."
)

DESCRIPTION = "Read the contents of a file"

FILE_READ_PROMPT = """Use this tool to read the contents of a file. You can:
1. Read the entire file
2. Read a specific range of lines (startLine to endLine)
3. Read image files (they will be base64 encoded)

For large files, use line ranges to read only what you need.
Binary files (non-text, non-image) cannot be read."""
