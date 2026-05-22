"""Model migration notifications — mirrors src/hooks/notifs/useModelMigrationNotifications.ts."""
from __future__ import annotations

async def useModelMigrationNotifications() -> list[dict] | None:
    """Notify when model migration is available."""
    return [{"type": "info", "message": "New model version available"}]

use_model_migration_notifications = useModelMigrationNotifications
