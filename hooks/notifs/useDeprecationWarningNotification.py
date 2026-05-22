"""Deprecation warning notification — mirrors src/hooks/notifs/useDeprecationWarningNotification.ts."""
from __future__ import annotations

async def useDeprecationWarningNotification(deprecated_item: str, replacement: str | None = None) -> dict[str, str] | None:
    """Emit deprecation warning notification."""
    msg = f"Deprecated: {deprecated_item}"
    if replacement:
        msg += f". Use {replacement} instead."
    return {"type": "warning", "message": msg}

use_deprecation_warning_notification = useDeprecationWarningNotification
