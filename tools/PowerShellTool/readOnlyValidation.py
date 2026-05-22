"""PowerShell read-only validation — mirrors src/tools/PowerShellTool/readOnlyValidation.ts"""
from typing import Dict, List

READ_ONLY_SAFE_COMMANDS: List[str] = [
    "Get-",
    "Select-",
    "Where-",
    "Sort-",
    "Group-",
    "Measure-",
    "Compare-",
    "Format-List",
    "Format-Table",
    "Out-GridView",
    "Export-Csv",
    "Export-Clixml",
    "Tee-Object",
]

def isReadOnlyCommand(command: str) -> bool:
    """Check if a PowerShell command is read-only."""
    cmd = command.strip()
    for prefix in READ_ONLY_SAFE_COMMANDS:
        if cmd.lower().startswith(prefix.lower()):
            return True
    return False

def checkReadOnlyConstraints(command: str, mode: str) -> Dict[str, str]:
    """Check read-only constraints for a command."""
    if mode == "readOnly" and not isReadOnlyCommand(command):
        return {
            "result": "deny",
            "message": f"Command '{command}' is not read-only. Read-only mode only allows read operations.",
        }
    return {"result": "allow"}
