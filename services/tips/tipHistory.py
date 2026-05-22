"""Tip history tracking — mirrors src/services/tips/tipHistory.ts."""
from __future__ import annotations


def recordTipShown(tip_id: str) -> None:
    """Record that a tip was shown in this session.

    Mirrors recordTipShown() from tipHistory.ts.
    """
    try:
        from ...utils.config import get_global_config, save_global_config
        num_startups = get_global_config().get("numStartups", 0)

        def updater(c: dict) -> dict:
            history = c.get("tipsHistory") or {}
            if history.get(tip_id) == num_startups:
                return c
            return {**c, "tipsHistory": {**history, tip_id: num_startups}}

        save_global_config(updater)
    except Exception:
        pass


def getSessionsSinceLastShown(tip_id: str) -> float:
    """Get the number of sessions since a tip was last shown.

    Returns infinity if never shown.
    Mirrors getSessionsSinceLastShown() from tipHistory.ts.
    """
    try:
        from ...utils.config import get_global_config
        config = get_global_config()
        last_shown = (config.get("tipsHistory") or {}).get(tip_id)
        if last_shown is None:
            return float("inf")
        return config.get("numStartups", 0) - last_shown
    except Exception:
        return float("inf")


record_tip_shown = recordTipShown
get_sessions_since_last_shown = getSessionsSinceLastShown
