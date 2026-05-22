"""Diff in IDE — mirrors src/hooks/useDiffInIDE.ts."""
from __future__ import annotations

async def useDiffInIDE(filePath: str = "") -> dict | None:
    """Show diff in IDE."""
    return {"file": filePath, "type": "diff"}

use_diff_in_ide = useDiffInIDE
