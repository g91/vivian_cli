"""PowerShell git safety — mirrors src/tools/PowerShellTool/gitSafety.ts"""
from typing import List

GIT_SAFE_COMMANDS: List[str] = [
    "git status",
    "git log",
    "git diff",
    "git branch",
    "git show",
    "git stash list",
    "git remote",
    "git config",
]

def isSafeGitCommand(command: str) -> bool:
    """Check if a git command is considered safe (read-only)."""
    cmd_lower = command.lower().strip()
    for safe in GIT_SAFE_COMMANDS:
        if cmd_lower.startswith(safe):
            return True
    return False
