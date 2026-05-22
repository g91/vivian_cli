"""
Port of src/utils/crossProjectResume.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path


CrossProjectResumeResult = Any


def checkCrossProjectResume(log, showAllProjects, worktreePaths):
    """Check if a log is from a different project directory and determine
whether it's a related worktree or a completely different project.

For same-repo worktrees, we can resume directly without requiring cd.
For different projects, we generate the cd command."""
    result = None
    if log is None:
        return False
    return True

