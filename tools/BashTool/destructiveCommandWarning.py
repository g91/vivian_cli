"""
Detect potentially destructive bash commands — mirrors
src/tools/BashTool/destructiveCommandWarning.ts
"""
from __future__ import annotations
import re
from typing import List, NamedTuple, Optional


class DestructivePattern(NamedTuple):
    pattern: re.Pattern
    warning: str


_PATTERNS: List[DestructivePattern] = [
    DestructivePattern(re.compile(r"\bgit\s+reset\s+--hard\b"), "Note: may discard uncommitted changes"),
    DestructivePattern(re.compile(r"\bgit\s+push\b[^;&|\n]*[ \t](--force|--force-with-lease|-f)\b"), "Note: may overwrite remote history"),
    DestructivePattern(re.compile(r"\bgit\s+clean\b(?![^;&|\n]*(?:-[a-zA-Z]*n|--dry-run))[^;&|\n]*-[a-zA-Z]*f"), "Note: may permanently delete untracked files"),
    DestructivePattern(re.compile(r"\bgit\s+checkout\s+(--\s+)?\.[ \t]*($|[;&|\n])"), "Note: may discard all working tree changes"),
    DestructivePattern(re.compile(r"\bgit\s+restore\s+(--\s+)?\.[ \t]*($|[;&|\n])"), "Note: may discard all working tree changes"),
    DestructivePattern(re.compile(r"\bgit\s+stash[ \t]+(drop|clear)\b"), "Note: may permanently remove stashed changes"),
    DestructivePattern(re.compile(r"\bgit\s+branch\s+(-D[ \t]|--delete\s+--force|--force\s+--delete)\b"), "Note: may force-delete a branch"),
    DestructivePattern(re.compile(r"\bgit\s+(commit|push|merge)\b[^;&|\n]*--no-verify\b"), "Note: may skip safety hooks"),
    DestructivePattern(re.compile(r"\bgit\s+commit\b[^;&|\n]*--amend\b"), "Note: may rewrite the last commit"),
    DestructivePattern(re.compile(r"(^|[;&|\n]\s*)rm\s+-[a-zA-Z]*[rR][a-zA-Z]*f|(^|[;&|\n]\s*)rm\s+-[a-zA-Z]*f[a-zA-Z]*[rR]"), "Note: may recursively force-remove files"),
    DestructivePattern(re.compile(r"(^|[;&|\n]\s*)rm\s+-[a-zA-Z]*[rR]"), "Note: may recursively remove files"),
    DestructivePattern(re.compile(r"(^|[;&|\n]\s*)rm\s+-[a-zA-Z]*f"), "Note: may force-remove files"),
    DestructivePattern(re.compile(r"\b(DROP|TRUNCATE)\s+(TABLE|DATABASE|SCHEMA)\b", re.IGNORECASE), "Note: may drop or truncate database objects"),
    DestructivePattern(re.compile(r"\bDELETE\s+FROM\s+\w+[ \t]*(;|\"|\'|\n|$)", re.IGNORECASE), "Note: may delete all rows from a database table"),
    DestructivePattern(re.compile(r"\bterraform\s+(destroy|apply)\b"), "Note: may modify or destroy cloud infrastructure"),
    DestructivePattern(re.compile(r"\bkubectl\s+delete\b"), "Note: may delete Kubernetes resources"),
    DestructivePattern(re.compile(r"\baws\s+.*\s+delete\b"), "Note: may delete AWS resources"),
]


def getDestructiveCommandWarning(command: str) -> Optional[str]:
    """
    Detect potentially destructive bash commands and return a warning string.
    Returns None if no destructive patterns detected.
    """
    for dp in _PATTERNS:
        if dp.pattern.search(command):
            return dp.warning
    return None
