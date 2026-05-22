"""Teammate shutdown notification — mirrors src/hooks/notifs/useTeammateShutdownNotification.ts."""
from __future__ import annotations

async def useTeammateShutdownNotification() -> dict | None:
    """Notify when teammate connection is lost."""
    return {"type": "warning", "message": "Teammate connection lost"}

use_teammate_shutdown_notification = useTeammateShutdownNotification
