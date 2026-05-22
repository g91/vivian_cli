"""
BashTool read-only validation — mirrors src/tools/BashTool/readOnlyValidation.ts
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Set


# Commands that are safe in read-only mode
READ_ONLY_SAFE_COMMANDS: Set[str] = {
    "cat", "head", "tail", "less", "more", "grep", "rg", "find", "ls", "stat",
    "file", "wc", "diff", "git", "pwd", "echo", "printf", "which", "whereis",
    "env", "printenv", "uname", "hostname", "whoami", "id", "date", "uptime",
    "df", "du", "ps", "top", "free", "lsof", "netstat", "ss", "curl",
    "python3", "python", "node", "jq", "awk", "sed", "sort", "uniq", "tr",
    "cut", "paste", "column", "tee", "xargs", "basename", "dirname",
    "realpath", "readlink", "md5sum", "sha256sum", "sha1sum", "type",
    "command", "true", "false", "test", "[", "[[",
}

GIT_READ_ONLY_COMMANDS: Set[str] = {
    "git status", "git log", "git diff", "git show", "git branch",
    "git tag", "git remote", "git fetch", "git ls-files", "git cat-file",
    "git rev-parse", "git describe", "git stash list", "git blame", "git annotate",
}


def checkReadOnlyConstraints(
    input_data: Dict[str, Any],
    isReadOnly: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Check if a bash command violates read-only constraints.
    Returns None if OK, or a permission result dict if blocked.
    """
    if not isReadOnly:
        return None

    command = input_data.get("command", "")
    # Simple heuristic: check if the first command is read-only safe
    import re
    parts = re.split(r"[|;&]", command)
    for part in parts:
        baseCmd = part.strip().split()[0] if part.strip() else ""
        if baseCmd and baseCmd not in READ_ONLY_SAFE_COMMANDS:
            return {
                "behavior": "ask",
                "message": f"Command '{baseCmd}' may not be safe in read-only mode.",
                "decisionReason": {"type": "other", "reason": f"Command not in read-only safe list: {baseCmd}"},
            }
    return None
