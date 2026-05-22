"""NPM deprecation notification — mirrors src/hooks/notifs/useNpmDeprecationNotification.ts."""
from __future__ import annotations

async def useNpmDeprecationNotification(package: str = "") -> dict | None:
    """Notify if NPM package is deprecated."""
    if package:
        return {"type": "warning", "message": f"Package '{package}' is deprecated"}
    return None

use_npm_deprecation_notification = useNpmDeprecationNotification
