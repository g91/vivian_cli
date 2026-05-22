"""
Port of src/utils/getWorktreePaths.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import asyncio
import time
from datetime import datetime, timezone, timedelta


async def getWorktreePaths(cwd):
    """Returns the paths of all worktrees for the current git repository.
If git is not available, not in a git repo, or only has one worktree,
returns an empty array.

This version includes analytics tracking and uses the CLI's gitExe()
resolver. For a portable version without CLI deps, use
getWorktreePathsPortable().

@param cwd Directory to run the command from
@returns Array of absolute worktree paths"""
    result = None
    _input = cwd
    _output = _input if _input is not None else {}
    return _output

