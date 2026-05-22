"""Common constants — mirrors src/constants/common.ts."""
from __future__ import annotations

import os
from datetime import date, datetime
from functools import lru_cache


def getLocalISODate() -> str:
    """Get the LOCAL date in ISO format."""
    override = os.environ.get("vivian_CODE_OVERRIDE_DATE")
    if override:
        return override
    return date.today().isoformat()


@lru_cache(maxsize=1)
def getSessionStartDate() -> str:
    """Memoized date for prompt-cache stability."""
    return getLocalISODate()


def getLocalMonthYear() -> str:
    """Returns 'Month YYYY' in the user's local timezone."""
    override = os.environ.get("vivian_CODE_OVERRIDE_DATE")
    d = datetime.fromisoformat(override) if override else datetime.now()
    return d.strftime("%B %Y")


get_local_iso_date = getLocalISODate
get_session_start_date = getSessionStartDate
get_local_month_year = getLocalMonthYear
