"""Memory version detection — mirrors src/utils/memory/versions.ts"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def _find_git_root(cwd: str) -> Optional[str]:
    """Walk up from cwd looking for a .git directory."""
    p = Path(cwd)
    while True:
        if (p / ".git").exists():
            return str(p)
        parent = p.parent
        if parent == p:
            return None
        p = parent


def project_is_in_git_repo(cwd: str) -> bool:
    """Return True if cwd is inside a git repository.

    Mirrors projectIsInGitRepo() from versions.ts.
    Uses only filesystem access (no subprocess).
    """
    return _find_git_root(cwd) is not None
