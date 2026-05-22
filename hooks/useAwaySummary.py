"""Away mode summary — mirrors src/hooks/useAwaySummary.ts."""
from __future__ import annotations

def useAwaySummary(isAway: bool = False) -> dict:
    """Generate summary during away mode."""
    return {
        "isAway": isAway,
        "summary": "Away mode active" if isAway else "",
    }

use_away_summary = useAwaySummary
