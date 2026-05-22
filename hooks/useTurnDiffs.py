"""Turn diffs — mirrors src/hooks/useTurnDiffs.ts."""
from __future__ import annotations

def useTurnDiffs() -> dict:
    """Track turn differences."""
    return {"diffs": []}

use_turn_diffs = useTurnDiffs
