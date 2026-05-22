"""FileEditTool package — mirrors src/tools/FileEditTool/"""
from .constants import (
    FILE_EDIT_TOOL_NAME,
    vivian_FOLDER_PERMISSION_PATTERN,
    GLOBAL_vivian_FOLDER_PERMISSION_PATTERN,
    FILE_UNEXPECTEDLY_MODIFIED_ERROR,
)
from .editFile import FileEditError, applyEdit, countOccurrences, editFile
from .FileEditTool import TOOL_NAME, INPUT_SCHEMA, OUTPUT_SCHEMA, call, description, prompt

__all__ = [
    "FILE_EDIT_TOOL_NAME",
    "vivian_FOLDER_PERMISSION_PATTERN",
    "GLOBAL_vivian_FOLDER_PERMISSION_PATTERN",
    "FILE_UNEXPECTEDLY_MODIFIED_ERROR",
    "FileEditError",
    "applyEdit",
    "countOccurrences",
    "editFile",
    "TOOL_NAME",
    "INPUT_SCHEMA",
    "OUTPUT_SCHEMA",
    "call",
    "description",
    "prompt",
]
