"""
Port of src/utils/task/outputFormatting.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path


TASK_MAX_OUTPUT_UPPER_LIMIT: Any = 160_000
TASK_MAX_OUTPUT_DEFAULT: Any = 32_000


def getMaxTaskOutputLength():
    result = validateBoundedIntEnvVar(
    'TASK_MAX_OUTPUT_LENGTH',
    os.environ.get("TASK_MAX_OUTPUT_LENGTH", ""),
    TASK_MAX_OUTPUT_DEFAULT,
    TASK_MAX_OUTPUT_UPPER_LIMIT,
    )
    return result.effective


def formatTaskOutput(output, taskId):
    """Format task output for API consumption, truncating if too large.
When truncated, includes a header with the file path and returns
the last N characters that fit within the limit."""
    content; wasTruncated

