"""IDE status indicator — mirrors src/hooks/notifs/useIDEStatusIndicator.ts."""
from __future__ import annotations

def useIDEStatusIndicator(status: str = "idle") -> dict:
    """Display IDE status indicator."""
    return {"status": status, "visible": True}

use_ide_status_indicator = useIDEStatusIndicator
