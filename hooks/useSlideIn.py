"""Slide in animation — mirrors src/hooks/useSlideIn.ts."""
from __future__ import annotations

def useSlideIn(duration: int = 300) -> dict:
    """Slide in animation control."""
    return {"animating": False, "duration": duration}

use_slide_in = useSlideIn
