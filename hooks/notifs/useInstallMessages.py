"""Install messages notification — mirrors src/hooks/notifs/useInstallMessages.ts."""
from __future__ import annotations

async def useInstallMessages(packageName: str = "") -> dict | None:
    """Display installation progress/status messages."""
    return {
        "type": "info",
        "message": f"Installing {packageName}" if packageName else "Installation in progress...",
    }

use_install_messages = useInstallMessages
