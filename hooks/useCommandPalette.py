"""Command palette — mirrors src/hooks/useCommandPalette.ts."""
from __future__ import annotations
from typing import Any

def useCommandPalette(commands: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Quick command palette access."""
    return {
        "commands": commands or [],
        "visible": False,
        "toggle": lambda: None,
    }

use_command_palette = useCommandPalette
