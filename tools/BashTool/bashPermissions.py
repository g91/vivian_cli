"""
BashTool permission evaluation — mirrors src/tools/BashTool/bashPermissions.ts
"""
from __future__ import annotations
import fnmatch
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

# Environment variable names that are used for binary hijacking
BINARY_HIJACK_VARS: Set[str] = {
    "PATH", "LD_PRELOAD", "LD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES",
    "DYLD_LIBRARY_PATH", "PYTHONPATH", "NODE_PATH", "JAVA_HOME",
    "RUBYLIB", "PERL5LIB", "GEM_PATH",
}

# Safe wrapper commands that don't change the semantics
SAFE_WRAPPER_COMMANDS: Set[str] = {
    "sudo", "nice", "ionice", "nohup", "time", "env", "strace", "ltrace",
    "timeout", "tee",
}


def stripSafeWrappers(command: str) -> str:
    """Strip safe wrapper commands from the front of a command."""
    parts = command.strip().split()
    while parts and parts[0] in SAFE_WRAPPER_COMMANDS:
        parts = parts[1:]
        # Skip env var assignments like KEY=VALUE
        while parts and "=" in parts[0] and not parts[0].startswith("-"):
            parts = parts[1:]
    return " ".join(parts)


def stripAllLeadingEnvVars(command: str) -> str:
    """Strip all leading environment variable assignments."""
    parts = command.strip().split()
    while parts and "=" in parts[0] and not parts[0].startswith("-"):
        parts = parts[1:]
    return " ".join(parts)


def matchWildcardPattern(pattern: str, value: str) -> bool:
    """Match a value against a wildcard pattern (supports * and ?)."""
    return fnmatch.fnmatch(value, pattern)


def permissionRuleExtractPrefix(rule: str) -> str:
    """Extract the literal prefix from a permission rule (before any wildcard)."""
    idx = min(
        (rule.find(c) for c in ("*", "?", "[") if c in rule),
        default=len(rule)
    )
    return rule[:idx]


def commandHasAnyCd(command: str) -> bool:
    """Check if a command contains any cd subcommands."""
    parts = re.split(r"[|;&]", command)
    for part in parts:
        stripped = part.strip().split()[0] if part.strip() else ""
        if stripped == "cd":
            return True
    return False


def isNormalizedCdCommand(command: str) -> bool:
    """Check if a command is a normalized cd command."""
    stripped = command.strip()
    return stripped == "cd" or stripped.startswith("cd ")


def isNormalizedGitCommand(command: str) -> bool:
    """Check if a command is a normalized git command."""
    stripped = command.strip()
    return stripped == "git" or stripped.startswith("git ")


def bashPermissionRule(pattern: str) -> str:
    """Normalize a bash permission rule pattern."""
    return pattern.strip()


def bashToolHasPermission(
    input_data: Dict[str, Any],
    allowedCommands: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Check if a bash command has permission to run based on allowlists.
    Returns a permission result dict.
    """
    command = input_data.get("command", "")

    if not allowedCommands:
        return {
            "behavior": "ask",
            "message": "No permission rules configured",
            "decisionReason": {"type": "other", "reason": "No permission rules"},
        }

    for pattern in allowedCommands:
        if matchWildcardPattern(pattern, command) or command.startswith(permissionRuleExtractPrefix(pattern)):
            return {
                "behavior": "allow",
                "updatedInput": input_data,
                "decisionReason": {"type": "rule", "rule": pattern},
            }

    return {
        "behavior": "ask",
        "message": f"Command not in allowlist: {command[:100]}",
        "decisionReason": {"type": "other", "reason": "Command not in allowlist"},
    }
