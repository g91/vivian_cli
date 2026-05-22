"""Chrome extension notification — mirrors src/hooks/useChromeExtensionNotification.ts."""
from __future__ import annotations

async def useChromeExtensionNotification() -> dict | None:
    """Notify if Chrome extension is available."""
    return {"type": "info", "message": "Install Chrome extension for enhanced features"}

use_chrome_extension_notification = useChromeExtensionNotification
