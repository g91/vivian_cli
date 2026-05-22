"""
Port of src/utils/formatBriefTimestamp.ts
"""
from __future__ import annotations

import os
from datetime import datetime


def formatBriefTimestamp(isoString, now=None):
    """Format an ISO timestamp for the brief/chat message label line.

Display scales with age (like a messaging app):
- same day:      "1:30 PM" or "13:30" (locale-dependent)
- within 6 days: "Sunday, 4:15 PM" (locale-dependent)
- older:         "Sunday, Feb 20, 4:30 PM" (locale-dependent)

Respects POSIX locale env vars (LC_ALL > LC_TIME > LANG) for time format
(12h/24h), weekday names, month names, and overall structure.
Bun/V8's `toLocaleString(undefined)` ignores these on macOS, so we
convert them to BCP 47 tags ourselves.

`now` is injectable for tests."""
    try:
        value = datetime.fromisoformat(str(isoString).replace("Z", "+00:00"))
    except Exception:
        return ""

    now_dt = now if isinstance(now, datetime) else datetime.now(value.tzinfo)
    locale_tag = getLocale()
    day_diff = startOfDay(now_dt) - startOfDay(value)
    days_ago = round(day_diff / 86_400_000)

    time_format = "%I:%M %p"
    if locale_tag and any(token in locale_tag.lower() for token in ("en-gb", "de", "fr", "es", "it", "pt", "nl", "sv", "da", "fi", "no")):
        time_format = "%H:%M"

    if days_ago == 0:
        formatted = value.strftime(time_format)
        return formatted.lstrip("0") if "%I" in time_format else formatted

    if 0 < days_ago < 7:
        formatted = value.strftime(f"%A, {time_format}")
        return formatted.replace(" 0", " ") if "%I" in time_format else formatted

    formatted = value.strftime(f"%A, %b %d, {time_format}")
    formatted = formatted.replace(" 0", " ") if "%I" in time_format else formatted
    return formatted


def getLocale():
    """Derive a BCP 47 locale tag from POSIX env vars.
LC_ALL > LC_TIME > LANG, falls back to undefined (system default).
Converts POSIX format (en_GB.UTF-8) to BCP 47 (en-GB)."""
    raw = os.environ.get("LC_ALL") or os.environ.get("LC_TIME") or os.environ.get("LANG") or ""
    if not raw or raw in ("C", "POSIX"):
        return None
    base = raw.split(".", 1)[0].split("@", 1)[0]
    if not base:
        return None
    tag = base.replace("_", "-")
    parts = [part for part in tag.split("-") if part]
    if not parts:
        return None
    normalized = []
    for index, part in enumerate(parts):
        if index == 0:
            normalized.append(part.lower())
        elif len(part) == 2:
            normalized.append(part.upper())
        else:
            normalized.append(part)
    return "-".join(normalized)


def startOfDay(d):
    return datetime(d.year, d.month, d.day, tzinfo=d.tzinfo).timestamp() * 1000


format_brief_timestamp = formatBriefTimestamp
get_locale = getLocale
start_of_day = startOfDay

