"""Direct connect — mirrors src/hooks/useDirectConnect.ts."""
from __future__ import annotations

async def useDirectConnect() -> bool:
    """Check if direct connection is available."""
    return True

use_direct_connect = useDirectConnect
