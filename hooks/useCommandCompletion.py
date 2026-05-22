"""Command completion — mirrors src/hooks/useCommandCompletion.ts."""
from __future__ import annotations
from typing import Any

def useCommandCompletion(commands: list[str] | None = None) -> dict[str, Any]:
    """Provide command completion suggestions."""
    def complete(prefix: str) -> list[str]:
        cmd_list = commands or []
        return [c for c in cmd_list if c.startswith(prefix)]
    
    return {
        "commands": commands or [],
        "complete": complete,
    }

use_command_completion = useCommandCompletion
