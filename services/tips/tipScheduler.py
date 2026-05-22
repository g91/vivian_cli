"""Tip scheduler — mirrors src/services/tips/tipScheduler.ts."""
from __future__ import annotations

from typing import Optional


Tip = dict  # {id, cooldownSessions, ...}
TipContext = dict


def selectTipWithLongestTimeSinceShown(available_tips: list[Tip]) -> Optional[Tip]:
    """Select the tip that was shown longest ago.

    Mirrors selectTipWithLongestTimeSinceShown() from tipScheduler.ts.
    """
    if not available_tips:
        return None
    if len(available_tips) == 1:
        return available_tips[0]

    from .tipHistory import getSessionsSinceLastShown

    tips_with_sessions = [
        {"tip": t, "sessions": getSessionsSinceLastShown(t["id"])}
        for t in available_tips
    ]
    tips_with_sessions.sort(key=lambda x: x["sessions"], reverse=True)
    return tips_with_sessions[0]["tip"]


async def getTipToShowOnSpinner(context: Optional[TipContext] = None) -> Optional[Tip]:
    """Get the tip to show on the spinner, respecting settings and cooldowns.

    Mirrors getTipToShowOnSpinner() from tipScheduler.ts.
    """
    try:
        from ...utils.settings.settings import get_settings_deprecated
        if get_settings_deprecated().get("spinnerTipsEnabled") is False:
            return None
    except Exception:
        pass

    try:
        from .tipRegistry import getRelevantTips
        tips = await getRelevantTips(context)
    except Exception:
        return None

    if not tips:
        return None
    return selectTipWithLongestTimeSinceShown(tips)


def recordShownTip(tip: Tip) -> None:
    """Record a shown tip in history and analytics.

    Mirrors recordShownTip() from tipScheduler.ts.
    """
    from .tipHistory import recordTipShown
    recordTipShown(tip["id"])

    try:
        from ..analytics.index import logEvent
        logEvent("tengu_tip_shown", {
            "tipIdLength": tip["id"],
            "cooldownSessions": tip.get("cooldownSessions"),
        })
    except Exception:
        pass


select_tip_with_longest_time_since_shown = selectTipWithLongestTimeSinceShown
get_tip_to_show_on_spinner = getTipToShowOnSpinner
record_shown_tip = recordShownTip
