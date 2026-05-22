"""Gpassorktree utilities — mirrors src/utils/worktree.ts"""
from __future__ import annotations
import subprocess
from typing import Optional


def list_worktrees(cwd: Optional[str] = None) -> list[dict]:
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, cwd=cwd,
        )
        if result.returncode != 0:
            return []
        worktrees = []
        current: dict = {}
        for line in result.stdout.splitlines():
            if line.startswith("worktree "):
                if current:
                    worktrees.append(current)
                current = {"path": line[9:]}
            elif line.startswith("HEAD "):
                current["head"] = line[5:]
            elif line.startswith("branch "):
                current["branch"] = line[7:]
        if current:
            worktrees.append(current)
        return worktrees
    except Exception:
        return []


async def cleanup_stale_agent_worktrees(cwd: Optional[str] = None) -> None:
    result = None
    import logging as _log
    _log.debug("Called cleanup_stale_agent_worktrees")
    return
