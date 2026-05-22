"""Tips package — mirrors src/services/tips/."""
from __future__ import annotations

from .tipHistory import recordTipShown, getSessionsSinceLastShown
from .tipRegistry import getRelevantTips, registerTip
from .tipScheduler import selectTipWithLongestTimeSinceShown, getTipToShowOnSpinner, recordShownTip

__all__ = [
    "recordTipShown",
    "getSessionsSinceLastShown",
    "getRelevantTips",
    "registerTip",
    "selectTipWithLongestTimeSinceShown",
    "getTipToShowOnSpinner",
    "recordShownTip",
]
