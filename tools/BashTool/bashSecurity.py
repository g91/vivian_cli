"""
BashTool security validation — mirrors src/tools/BashTool/bashSecurity.ts

Validates bash commands for security vulnerabilities before execution.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Set, Tuple


# Commands that are inherently safe to run
ALWAYS_SAFE_COMMANDS: Set[str] = {
    "echo", "printf", "true", "false", ":", "pwd", "date", "whoami", "id",
    "uname", "hostname", "env", "printenv", "ls", "cat", "head", "tail",
    "grep", "find", "wc", "stat", "file", "which", "whereis", "type",
}

# Dangerous operators that can chain unsafe commands
DANGEROUS_OPERATORS = frozenset(["$(", "`", "${", "eval", "exec"])


def _containsDangerousSubstitution(command: str) -> bool:
    """Check for command substitution patterns that could be exploited."""
    for op in ("$(", "`"):
        if op in command:
            return True
    return False


def bashCommandIsSafe_DEPRECATED(command: str) -> bool:
    """
    Legacy safety check — deprecated in favor of full AST-based parsing.
    Returns True if the command appears safe based on simple heuristics.
    """
    stripped = command.strip()
    if not stripped:
        return True

    # Split on operators
    parts = re.split(r"[|;&]", stripped)
    for part in parts:
        tokens = part.strip().split()
        if not tokens:
            continue
        baseCmd = tokens[0]
        if baseCmd not in ALWAYS_SAFE_COMMANDS:
            return False

    return True


async def bashCommandIsSafeAsync_DEPRECATED(command: str) -> bool:
    """Async wrapper for bashCommandIsSafe_DEPRECATED."""
    return bashCommandIsSafe_DEPRECATED(command)


def parseForSecurity(command: str) -> Dict[str, Any]:
    """
    Parse a command for security issues.
    Returns a dict with 'safe': bool and 'reason': str.
    """
    # Check for null bytes (injection attempt)
    if "\x00" in command or "\0" in command:
        return {"safe": False, "reason": "Command contains null bytes"}

    # Check for overly long commands
    if len(command) > 100_000:
        return {"safe": False, "reason": "Command exceeds length limit"}

    return {"safe": True, "reason": None}
