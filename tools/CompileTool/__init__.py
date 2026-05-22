"""CompileTool package — cross-platform C/C++ (and more) compiler tool."""
from .CompileTool import (
    TOOL_NAME,
    INPUT_SCHEMA,
    OUTPUT_SCHEMA,
    call,
    description,
    prompt,
    userFacingName,
    getToolUseSummary,
    detect_compilers,
)

__all__ = [
    "TOOL_NAME",
    "INPUT_SCHEMA",
    "OUTPUT_SCHEMA",
    "call",
    "description",
    "prompt",
    "userFacingName",
    "getToolUseSummary",
    "detect_compilers",
]
