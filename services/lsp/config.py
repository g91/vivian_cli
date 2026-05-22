"""LSP config — mirrors src/services/lsp/config.ts."""
from __future__ import annotations
from typing import Optional


async def getAllLspServers() -> dict:
    """Get all configured LSP servers from plugins.

    Mirrors getAllLspServers() from config.ts.
    """
    return {"servers": {}}


get_all_lsp_servers = getAllLspServers
