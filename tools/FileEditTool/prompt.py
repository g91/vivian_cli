"""FileEditTool prompt — mirrors src/tools/FileEditTool/prompt.ts"""
from .constants import FILE_EDIT_TOOL_NAME

DESCRIPTION = (
    f"Edit files by replacing specific text using exact string matching. "
    f"Supports single and multiple replacements in one call."
)

PROMPT = f"""Use this tool to make precise edits to existing files.

Parameters:
- file_path: Absolute path to the file to edit
- old_string: EXACT string to find (must appear exactly once, include surrounding context)
- new_string: Replacement text for old_string

Important:
- old_string must match the existing file content EXACTLY (whitespace, indentation)
- Include enough context lines to uniquely identify the location
- If a string appears multiple times, add more context to make it unique
- For new files, create them with Write first
- Never use this to create files; use Write instead
"""
