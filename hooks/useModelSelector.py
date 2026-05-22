"""Model selector — mirrors src/hooks/useModelSelector.ts."""
from __future__ import annotations

def useModelSelector(models: list[str] | None = None) -> dict:
    """Select AI model."""
    return {"models": models or [], "selected": None}

use_model_selector = useModelSelector
