"""PR status — mirrors src/hooks/usePrStatus.ts."""
from __future__ import annotations

async def usePrStatus() -> dict:
    """Track PR status."""
    return {"status": None}

use_pr_status = usePrStatus
