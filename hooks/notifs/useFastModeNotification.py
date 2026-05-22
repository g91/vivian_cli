"""Fast mode notification — mirrors src/hooks/notifs/useFastModeNotification.ts."""
from __future__ import annotations

async def useFastModeNotification(enabled: bool = False) -> dict | None:
    """Notify when fast mode is enabled/disabled."""
    if enabled:
        return {"type": "info", "message": "Fast mode enabled"}
    return None

use_fast_mode_notification = useFastModeNotification
