"""LSP plugin recommendation — mirrors src/hooks/useLspPluginRecommendation.ts."""
from __future__ import annotations

async def useLspPluginRecommendation() -> dict | None:
    """Recommend LSP plugin."""
    return {"plugin": "lsp-plugin", "recommended": False}

use_lsp_plugin_recommendation = useLspPluginRecommendation
