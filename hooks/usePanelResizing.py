"""Panel resizing — mirrors src/hooks/usePanelResizing.ts."""
from __future__ import annotations

def usePanelResizing() -> dict:
    """Manage panel resize state."""
    return {"resizing": False, "position": 0}

use_panel_resizing = usePanelResizing
