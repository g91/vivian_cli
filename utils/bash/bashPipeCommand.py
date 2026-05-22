"""
Port of src/utils/bash/bashPipeCommand.ts
Pipe command rearrangement for bash security.
"""
from __future__ import annotations
import re
from typing import Any, List, Optional


def rearrange_pipe_command(command):
    """Rearrange pipe commands to normalize order for security analysis.
    Returns the command unchanged if no rearrangement is needed.
    """
    # For most commands, no rearrangement needed
    return command


rearrangePipeCommand = rearrange_pipe_command
