"""Plugin auto-update notification — mirrors src/hooks/notifs/usePluginAutoupdateNotification.ts."""
from __future__ import annotations

async def usePluginAutoupdateNotification() -> dict | None:
    """Notify when plugins are auto-updating."""
    return {"type": "info", "message": "Updating plugins..."}

use_plugin_autoupdate_notification = usePluginAutoupdateNotification
