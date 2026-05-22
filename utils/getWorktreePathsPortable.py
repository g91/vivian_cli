"""Port of src/utils/getWorktreePathsPortable.ts."""

from __future__ import annotations

import asyncio
import unicodedata


async def getWorktreePathsPortable(cwd):
    """Return git worktree paths using only subprocess primitives."""
    try:
        process = await asyncio.create_subprocess_exec(
            'git',
            'worktree',
            'list',
            '--porcelain',
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _stderr = await asyncio.wait_for(process.communicate(), timeout=5)
    except Exception:
        return []

    if process.returncode != 0 or not stdout:
        return []

    return [
        unicodedata.normalize('NFC', line[len('worktree '):].strip())
        for line in stdout.decode('utf-8', errors='replace').splitlines()
        if line.startswith('worktree ')
    ]


get_worktree_paths_portable = getWorktreePathsPortable

