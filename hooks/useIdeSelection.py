"""IDE selection — mirrors src/hooks/useIdeSelection.ts."""
from __future__ import annotations

def useIdeSelection() -> dict:
    """Get IDE selection context."""
    return {"text": "", "range": None}

use_ide_selection = useIdeSelection
