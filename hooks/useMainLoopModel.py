"""Main loop model — mirrors src/hooks/useMainLoopModel.ts."""
from __future__ import annotations

def useMainLoopModel() -> dict:
    """Main event loop model."""
    return {"running": True}

use_main_loop_model = useMainLoopModel
