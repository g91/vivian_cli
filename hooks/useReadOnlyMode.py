"""Read-only mode — mirrors src/hooks/useReadOnlyMode.ts."""
from __future__ import annotations

def useReadOnlyMode(enabled: bool = False) -> dict:
    """Toggle read-only mode."""
    return {"enabled": enabled}

use_read_only_mode = useReadOnlyMode
