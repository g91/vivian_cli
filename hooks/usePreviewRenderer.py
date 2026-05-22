"""Preview renderer — mirrors src/hooks/usePreviewRenderer.ts."""
from __future__ import annotations

def usePreviewRenderer(content: str = "") -> dict:
    """Render content preview."""
    return {"content": content, "html": content}

use_preview_renderer = usePreviewRenderer
