"""LSP initialization notification — mirrors src/hooks/notifs/useLspInitializationNotification.ts."""
from __future__ import annotations

async def useLspInitializationNotification() -> dict | None:
    """Notify when LSP is initializing."""
    return {"type": "info", "message": "Initializing language server..."}

use_lsp_initialization_notification = useLspInitializationNotification
