"""
Sed command validation — mirrors src/tools/BashTool/sedValidation.ts
"""
from __future__ import annotations
import re
import shlex
from typing import Any, Dict, List, Optional


ALLOWED_LINE_PRINT_FLAGS = {"-n", "--quiet", "--silent", "-E", "--regexp-extended",
                             "-r", "-z", "--zero-terminated", "--posix"}

ALLOWED_SED_FLAGS = {"-n", "--quiet", "--silent", "-E", "--regexp-extended",
                     "-r", "-e", "--expression", "-z", "--zero-terminated",
                     "-i", "--in-place", "--posix"}


def isLinePrintingCommand(command: str, expressions: List[str]) -> bool:
    """Check if this is a line printing command with -n flag."""
    if not re.match(r"^\s*sed\s+", command):
        return False
    try:
        tokens = shlex.split(command.split("sed", 1)[1])
    except ValueError:
        return False

    has_n_flag = False
    for tok in tokens:
        if tok in ("-n", "--quiet", "--silent"):
            has_n_flag = True
        elif tok.startswith("-") and not tok.startswith("--"):
            # Combined flags
            for c in tok[1:]:
                if f"-{c}" not in ALLOWED_LINE_PRINT_FLAGS:
                    return False
        elif tok.startswith("-"):
            if tok not in ALLOWED_LINE_PRINT_FLAGS:
                return False

    if not has_n_flag:
        return False

    # Validate expressions are print commands
    for expr in expressions:
        if not re.match(r"^\d+(,\d+)?[pP](;\d+(,\d+)?[pP])*$", expr):
            return False

    return True


def sedCommandIsAllowedByAllowlist(
    command: str,
    allowedPaths: Optional[List[str]] = None,
) -> bool:
    """Check if a sed command is allowed by the permission allowlist."""
    # Basic validation: must be a sed command
    if not re.match(r"^\s*sed\s+", command.strip()):
        return False

    # Check for dangerous patterns
    dangerous_patterns = [
        r"\bexec\b",
        r"\br\s+",  # sed read file
        r"\bw\s+",  # sed write file
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, command):
            return False

    return True
