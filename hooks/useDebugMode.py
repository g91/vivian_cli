"""Debug mode — mirrors src/hooks/useDebugMode.ts."""
from __future__ import annotations

def useDebugMode(enabled: bool = False) -> dict:
    """Enable/disable debug mode."""
    return {"enabled": enabled}

use_debug_mode = useDebugMode
