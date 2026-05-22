"""PowerShell command semantics — mirrors src/tools/PowerShellTool/commandSemantics.ts"""
from typing import Any, Dict

COMMAND_SEMANTICS: Dict[str, Dict[str, Any]] = {
    "Get-ChildItem": {"isRead": True, "isSearch": False, "isList": True},
    "Get-Content": {"isRead": True, "isSearch": False, "isList": False},
    "Select-String": {"isRead": False, "isSearch": True, "isList": False},
    "Get-Item": {"isRead": True, "isSearch": False, "isList": False},
    "Get-Location": {"isRead": True, "isSearch": False, "isList": False},
    "Test-Path": {"isRead": True, "isSearch": False, "isList": False},
}

def interpretCommandResult(command: str, exitCode: int, stdout: str, stderr: str) -> Dict[str, Any]:
    """Interpret the result of a PowerShell command."""
    return {
        "command": command,
        "exitCode": exitCode,
        "stdout": stdout,
        "stderr": stderr,
        "isError": exitCode != 0,
    }
