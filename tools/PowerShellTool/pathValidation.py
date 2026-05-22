"""PowerShell path validation — mirrors src/tools/PowerShellTool/pathValidation.ts"""
from typing import List, Optional

DANGEROUS_REMOVAL_PATHS: List[str] = [
    "C:\\",
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "/",
    "/etc",
    "/usr",
    "/home",
    "~",
    "$HOME",
    "$env:USERPROFILE",
]

def isDangerousRemovalPath(path: str) -> bool:
    """Check if a path is considered dangerous for removal operations."""
    normalized = path.strip().rstrip("\\/")
    for dangerous in DANGEROUS_REMOVAL_PATHS:
        if normalized.lower() == dangerous.lower():
            return True
    return False

def validatePathForCommand(path: str, command: str) -> Optional[str]:
    """Validate a path for a given command. Returns error message or None."""
    if any(kw in command.lower() for kw in ["remove", "delete", "rm ", "del "]):
        if isDangerousRemovalPath(path):
            return f"Refusing to remove dangerous path: {path}"
    return None
