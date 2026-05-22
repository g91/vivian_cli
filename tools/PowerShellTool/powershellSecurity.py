"""PowerShell security — mirrors src/tools/PowerShellTool/powershellSecurity.ts"""
from typing import List

ALWAYS_SAFE_COMMANDS: List[str] = [
    "Get-Help",
    "Get-Command",
    "Get-Member",
    "Get-Module",
    "Get-PSDrive",
    "Get-PSProvider",
    "Get-Variable",
    "Get-Alias",
]

DANGEROUS_OPERATORS: List[str] = [
    "| iex",
    "| Invoke-Expression",
    "| iwr",
    "| Invoke-WebRequest",
    "| irm",
    "| Invoke-RestMethod",
]

def isAlwaysSafeCommand(command: str) -> bool:
    """Check if a command is always considered safe."""
    cmd_lower = command.lower().strip()
    for safe in ALWAYS_SAFE_COMMANDS:
        if cmd_lower.startswith(safe.lower()):
            return True
    return False

def hasDangerousOperator(command: str) -> bool:
    """Check if a command contains dangerous operators."""
    cmd_lower = command.lower()
    for op in DANGEROUS_OPERATORS:
        if op.lower() in cmd_lower:
            return True
    return False
