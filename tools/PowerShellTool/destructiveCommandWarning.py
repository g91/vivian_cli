"""PowerShell destructive command warning — mirrors src/tools/PowerShellTool/destructiveCommandWarning.ts"""
from typing import List, Optional

DESTRUCTIVE_PATTERNS: List[str] = [
    r"Remove-Item\s+-Recurse",
    r"rm\s+-r",
    r"del\s+/f",
    r"Clear-Content",
    r"Set-Content",
    r"Out-File",
    r"Stop-Process",
    r"Stop-Service",
    r"Disable-",
    r"Uninstall-",
    r"Remove-",
    r"Format-",
    r"Initialize-",
    r"Reset-",
    r"Clear-",
    r"Invoke-Expression",
    r"iex\s",
]  # fmt: skip

def getDestructiveCommandWarning(command: str) -> Optional[str]:
    """Check if a command matches destructive patterns and return a warning."""
    import re
    for pattern in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return f"Warning: '{command}' may be destructive. Please review carefully."
    return None
