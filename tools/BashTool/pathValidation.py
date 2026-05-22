"""
BashTool path validation — mirrors src/tools/BashTool/pathValidation.ts
"""
from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


PathCommand = str  # Type alias

DANGEROUS_REMOVAL_PATHS: Set[str] = {
    "/", "/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/lib64",
    "/opt", "/proc", "/root", "/run", "/sbin", "/srv", "/sys",
    "/tmp", "/usr", "/var",
}


def isDangerousRemovalPath(path: str) -> bool:
    """Check if a path is a dangerous removal target."""
    normalized = os.path.normpath(path)
    return normalized in DANGEROUS_REMOVAL_PATHS or normalized == os.path.expanduser("~")


def checkDangerousRemovalPaths(
    command: str,
    args: List[str],
    cwd: str,
) -> Optional[Dict[str, Any]]:
    """Check if rm/rmdir targets dangerous paths."""
    for arg in args:
        if arg.startswith("-"):
            continue
        cleanPath = arg.strip("\'\"")
        if cleanPath.startswith("~"):
            cleanPath = os.path.expanduser(cleanPath)
        absPath = cleanPath if os.path.isabs(cleanPath) else os.path.join(cwd, cleanPath)
        absPath = os.path.normpath(absPath)
        if isDangerousRemovalPath(absPath):
            return {
                "behavior": "ask",
                "message": f"Dangerous {command} operation detected: '{absPath}\'\n\nThis command would remove a critical system directory.",
                "decisionReason": {"type": "other", "reason": f"Dangerous {command} operation on critical path: {absPath}"},
                "suggestions": [],
            }
    return None


def validatePathForBashCommand(
    command: str,
    args: List[str],
    cwd: str,
    allowedPaths: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Validate paths in a bash command against allowed paths."""
    if not allowedPaths:
        return None

    for arg in args:
        if arg.startswith("-"):
            continue
        cleanArg = arg.strip("\'\"")
        if not cleanArg:
            continue
        absPath = cleanArg if os.path.isabs(cleanArg) else os.path.join(cwd, cleanArg)
        absPath = os.path.normpath(absPath)

        allowed = any(
            absPath == p or absPath.startswith(p.rstrip("/") + "/")
            for p in allowedPaths
        )
        if not allowed:
            return {
                "behavior": "ask",
                "message": f"Path '{absPath}' is not in the allowed paths list.",
                "decisionReason": {"type": "other", "reason": f"Path not allowed: {absPath}"},
            }
    return None
