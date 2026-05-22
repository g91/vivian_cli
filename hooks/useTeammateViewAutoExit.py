"""Teammate view auto exit — mirrors src/hooks/useTeammateViewAutoExit.ts."""
from __future__ import annotations

def useTeammateViewAutoExit() -> dict:
    """Auto exit teammate view."""
    return {"autoExit": False}

use_teammate_view_auto_exit = useTeammateViewAutoExit
