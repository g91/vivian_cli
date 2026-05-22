"""Network status — mirrors src/hooks/useNetworkStatus.ts."""
from __future__ import annotations

def useNetworkStatus() -> dict:
    """Track network connection status."""
    return {"online": True, "type": "unknown"}

use_network_status = useNetworkStatus
