"""Rate limit warning notification — mirrors src/hooks/notifs/useRateLimitWarningNotification.ts."""
from __future__ import annotations

async def useRateLimitWarningNotification(remaining: int, resetIn: int) -> dict[str, str | int] | None:
    """Emit rate limit warning when approaching quota."""
    if remaining <= 10:
        return {
            "type": "warning",
            "message": f"Rate limit: {remaining} requests remaining. Resets in {resetIn}s.",
            "remaining": remaining,
            "resetIn": resetIn,
        }
    return None

use_rate_limit_warning_notification = useRateLimitWarningNotification
