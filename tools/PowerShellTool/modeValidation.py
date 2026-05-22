"""PowerShell mode validation — mirrors src/tools/PowerShellTool/modeValidation.ts"""
from typing import Any, Dict

def checkPermissionMode(input_data: Dict[str, Any], toolPermissionContext: Dict[str, Any]) -> Dict[str, Any]:
    """Check if the current permission mode allows this PowerShell command."""
    mode = toolPermissionContext.get("mode", "default")
    
    if mode == "bypassPermissions":
        return {"behavior": "allow", "updatedInput": input_data}
    
    if mode == "plan":
        return {"behavior": "deny", "message": "PowerShell commands are not allowed in plan mode."}
    
    return {"behavior": "allow", "updatedInput": input_data}
