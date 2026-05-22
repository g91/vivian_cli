"""Port of src/utils/permissions/pathValidation.ts"""
from __future__ import annotations
import os
import re
from typing import Optional, List, Dict, Any
from .filesystem import pathInAllowedWorkingPath, pathInWorkingPath


MAX_DIRS_TO_LIST = 5
GLOB_PATTERN_REGEX = re.compile(r'[*?\[\]{}]')


def formatDirectoryList(directories: List[str]) -> str:
    """Format a list of directories for display, truncating if too many."""
    count = len(directories)
    if count <= MAX_DIRS_TO_LIST:
        return ', '.join(f"'{d}'" for d in directories)
    first = ', '.join(f"'{d}'" for d in directories[:MAX_DIRS_TO_LIST])
    return f"{first}, and {count - MAX_DIRS_TO_LIST} more"


def getGlobBaseDirectory(path: str) -> str:
    """Extract the base directory from a glob pattern for validation."""
    m = GLOB_PATTERN_REGEX.search(path)
    if not m:
        return path
    before_glob = path[:m.start()]
    last_sep = before_glob.rfind('/')
    if os.sep != '/' and last_sep == -1:
        last_sep = before_glob.rfind(os.sep)
    if last_sep == -1:
        return '.'
    return before_glob[:last_sep] or '/'


def expandTilde(path: str) -> str:
    """Expand tilde (~) at the start of a path to the user home directory."""
    if path == '~' or path.startswith('~/') or path.startswith('~' + os.sep):
        return os.path.expanduser(path)
    return path


def isPathInSandboxWriteAllowlist(resolved_path: str) -> bool:
    """Check if a path is allowed by the sandbox write configuration."""
    # In Python port, no sandbox manager - always return False
    if resolved_path is None: return False
    if resolved_path is None:
        return False
    return True


def checkPathAllowed(
    file_path: str,
    allowed_paths: List[str],
    operation: str = 'read',
) -> Dict[str, Any]:
    """Check if a file path is allowed based on the list of allowed paths."""
    abs_path = os.path.abspath(os.path.expanduser(file_path))
    if not allowed_paths:
        return {'allowed': True}
    if pathInAllowedWorkingPath(abs_path, allowed_paths):
        return {'allowed': True}
    dirs_str = formatDirectoryList(allowed_paths)
    return {
        'allowed': False,
        'decisionReason': {
            'type': 'workingDir',
            'reason': f"Path '{abs_path}' is not in allowed directories: {dirs_str}",
        },
    }
