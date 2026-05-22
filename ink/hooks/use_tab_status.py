"""Port of src/ink/hooks/use-tab-status.ts."""
from __future__ import annotations

from typing import Any


def useTabStatus() -> dict[str, Any]:
    """Get the current tab status."""
    return {"isActive": True}


use_tab_status = useTabStatus
