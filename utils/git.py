"""Git utilities — mirrors selected src/utils/git.ts helpers."""
from __future__ import annotations

import subprocess
from typing import Optional


def _run_git(args: list[str], cwd: Optional[str] = None) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None

def get_current_branch(cwd: Optional[str] = None) -> Optional[str]:
    return _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)

def get_git_root(cwd: Optional[str] = None) -> Optional[str]:
    return _run_git(["rev-parse", "--show-toplevel"], cwd=cwd)


def get_remote_url(cwd: Optional[str] = None) -> Optional[str]:
    return _run_git(["remote", "get-url", "origin"], cwd=cwd)


getCurrentBranch = get_current_branch
getGitRoot = get_git_root
getRemoteUrl = get_remote_url
