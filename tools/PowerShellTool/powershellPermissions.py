"""PowerShell permissions — mirrors src/tools/PowerShellTool/powershellPermissions.ts"""
from typing import Any, Dict, List, Optional

def powershellPermissionRule(
    command: str,
    mode: str = "default",
) -> Dict[str, Any]:
    """Determine if a PowerShell command is allowed."""
    if mode == "bypassPermissions":
        return {"behavior": "allow"}
    
    # Always deny certain dangerous patterns
    dangerous = ["Format-", "Initialize-", "Clear-", "Remove-Item -Recurse"]
    for pattern in dangerous:
        if pattern.lower() in command.lower():
            return {
                "behavior": "deny",
                "message": f"Command matches dangerous pattern: {pattern}",
            }
    
    return {"behavior": "allow"}

def powershellToolHasPermission(
    input_data: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Check if the PowerShell tool has permission to execute."""
    command = input_data.get("command", "")
    mode = context.get("mode", "default")
    return powershellPermissionRule(command, mode)
