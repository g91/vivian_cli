"""Settings errors notification — mirrors src/hooks/notifs/useSettingsErrors.ts."""
from __future__ import annotations

async def useSettingsErrors(errors: list[str] | None = None) -> list[dict] | None:
    """Display settings validation errors."""
    if errors:
        return [{"type": "error", "message": e} for e in errors]
    return None

use_settings_errors = useSettingsErrors
