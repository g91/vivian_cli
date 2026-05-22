"""Command lookup — mirrors src/hooks/useCommandLookup.ts."""
from __future__ import annotations
from typing import Any

def useCommandLookup(commands: dict[str, Any] | None = None) -> dict[str, Any]:
    """Look up command metadata."""
    cmd_dict = commands or {}
    
    def lookup(name: str) -> Any:
        return cmd_dict.get(name, None)
    
    return {
        "lookup": lookup,
        "commands": cmd_dict,
    }

use_command_lookup = useCommandLookup
