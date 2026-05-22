"""MCP name normalization — mirrors src/services/mcp/normalization.ts."""
from __future__ import annotations

import re

vivianAI_SERVER_PREFIX = "api-vivian.d0a.net "


def normalizeNameForMCP(name: str) -> str:
    """Normalize server/tool names to be compatible with the API pattern ^[a-zA-Z0-9_-]{1,64}$.

    Mirrors normalizeNameForMCP() from normalization.ts.
    """
    normalized = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    if name.startswith(vivianAI_SERVER_PREFIX):
        normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


normalize_name_for_mcp = normalizeNameForMCP
