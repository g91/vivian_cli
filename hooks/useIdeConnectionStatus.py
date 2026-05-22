"""IDE connection status — mirrors src/hooks/useIdeConnectionStatus.ts."""
from __future__ import annotations

def useIdeConnectionStatus() -> dict:
    """Track IDE connection status."""
    return {"connected": True, "status": "connected"}

use_ide_connection_status = useIdeConnectionStatus
