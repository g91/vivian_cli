"""Presentation mode — mirrors src/hooks/usePresentationMode.ts."""
from __future__ import annotations

def usePresentationMode(enabled: bool = False) -> dict:
    """Presentation/focus mode."""
    return {"enabled": enabled}

use_presentation_mode = usePresentationMode
