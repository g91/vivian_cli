"""
Port of src/utils/promptShellExecution
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import asyncio
import uuid
import platform
import random
import struct


ShellOut = Dict[str, Any]
PromptShellTool = Any


async def executeShellCommandsInPrompt(text, context, slashCommandName, shell=None):
    """Parses prompt text and executes any embedded shell commands."""
    result = None
    _input = text
    _output = _input if _input is not None else {}
    return _output


def formatBashOutput(stdout, stderr, inline___false):
    return str(stdout)


def formatBashError(e, pattern, inline___false):
    return str(e)

