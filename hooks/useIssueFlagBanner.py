"""Issue flag banner — mirrors src/hooks/useIssueFlagBanner.ts."""
from __future__ import annotations

async def useIssueFlagBanner() -> dict | None:
    """Display issue flag banner."""
    return {"visible": False}

use_issue_flag_banner = useIssueFlagBanner
