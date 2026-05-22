"""Auto mode unavailable notification — mirrors src/hooks/notifs/useAutoModeUnavailableNotification.ts."""
from __future__ import annotations

async def useAutoModeUnavailableNotification(reason: str = "") -> dict | None:
    """Emit notification when auto mode is unavailable."""
    return {
        "type": "warning",
        "message": f"Auto mode unavailable{f': {reason}' if reason else '.'}",
    }

use_auto_mode_unavailable_notification = useAutoModeUnavailableNotification
