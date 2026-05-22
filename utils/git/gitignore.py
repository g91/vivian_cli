"""gitignore utilities — mirrors src/utils/git/gitignore.ts"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional


async def is_path_gitignored(file_path: str, cwd: str) -> bool:
    """Check if *file_path* is ignored by git, running from *cwd*.

    Delegates to ``git check-ignore`` so all gitignore sources (local,
    nested, global, .git/info/exclude) are consulted with correct
    precedence.

    Exit-code semantics (matching git's own):
      0 → ignored
      1 → not ignored
      128 → not in a git repo (we return False so callers fail open)
    """
    try:
        result = subprocess.run(
            ["git", "check-ignore", file_path],
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except OSError:
        return False


def get_global_gitignore_path() -> str:
    """Return the path to the global gitignore file (~/.config/git/ignore)."""
    return str(Path.home() / ".config" / "git" / "ignore")


async def add_file_glob_rule_to_gitignore(
    filename: str,
    cwd: Optional[str] = None,
) -> None:
    """Add *filename* as a glob rule to the global gitignore if not already ignored.

    Skips if:
    - cwd is not inside a git repo
    - the pattern is already covered by any gitignore source

    Writes ``**/<filename>`` to ``~/.config/git/ignore``, creating the file
    (and directory) if necessary.
    """
    if cwd is None:
        cwd = os.getcwd()

    # Check if we're in a git repo
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            return
    except OSError:
        return

    gitignore_entry = f"**/{filename}"
    # For directory patterns (ending with /), test a sample file inside
    test_path = f"{filename}sample-file.txt" if filename.endswith("/") else filename

    if await is_path_gitignored(test_path, cwd):
        return  # Already covered by existing rules

    global_path = Path(get_global_gitignore_path())
    global_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        content = global_path.read_text(encoding="utf-8")
        if gitignore_entry in content:
            return  # Pattern already present
        global_path.open("a", encoding="utf-8").write(f"\n{gitignore_entry}\n")
    except FileNotFoundError:
        global_path.write_text(f"{gitignore_entry}\n", encoding="utf-8")
    except OSError:
        pass
