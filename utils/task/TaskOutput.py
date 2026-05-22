"""
Port of src/utils/task/TaskOutput.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import asyncio
import hashlib
import time
from datetime import datetime, timezone, timedelta
import math
import struct


ProgressCallback = Any


class TaskOutput:
    """Single source of truth for a shell command's output.

For bash commands (file mode): both stdout and stderr go directly to
a file via stdio fds — neither enters JS. Progress is extracted by
polling the file tail. getStderr() returns '' since stderr is
interleaved in the output file.

For hooks (pipe mode): data flows through writeStdout()/writeStderr()
and is buffered in memory, spilling to disk if it exceeds the limit."""

    def __init__(self, taskId=None, path=None, stdoutToFile=None, onProgress=None, maxMemory=None):
        self.taskId = taskId
        self.path = path
        self.stdoutToFile = stdoutToFile
        self.onProgress = onProgress
        self.maxMemory = maxMemory


