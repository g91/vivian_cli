"""
BashTool mode validation — mirrors src/tools/BashTool/modeValidation.ts
"""
from __future__ import annotations
import re
from typing import Any, Dict, List

ACCEPT_EDITS_ALLOWED_COMMANDS = frozenset(["mkdir", "touch", "rm", "rmdir", "mv", "cp", "sed"])


def _splitCommands(command: str) -> List[str]:
    import re
    return [s.strip() for s in re.split(r"[;&|]", command) if s.strip()]


def checkPermissionMode(
    input_data: Dict[str, Any],
    toolPermissionContext: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Checks if commands should be handled differently based on the current
    permission mode.
    - Returns 'allow' if the current mode permits auto-approval
    - Returns 'ask' if the command needs approval in current mode
    - Returns 'passthrough' if no mode-specific handling applies
    """
    mode = toolPermissionContext.get("mode", "")

    if mode in ("bypassPermissions", "dontAsk"):
        return {"behavior": "passthrough", "message": f"{mode} is handled in main permission flow"}

    command = input_data.get("command", "")
    commands = _splitCommands(command)

    for cmd in commands:
        parts = cmd.strip().split()
        baseCmd = parts[0] if parts else ""
        if not baseCmd:
            continue

        if mode == "acceptEdits" and baseCmd in ACCEPT_EDITS_ALLOWED_COMMANDS:
            return {
                "behavior": "allow",
                "updatedInput": {"command": cmd},
                "decisionReason": {"type": "mode", "mode": "acceptEdits"},
            }

    return {"behavior": "passthrough", "message": "No mode-specific validation required"}


def getAutoAllowedCommands(mode: str) -> List[str]:
    return list(ACCEPT_EDITS_ALLOWED_COMMANDS) if mode == "acceptEdits" else []
