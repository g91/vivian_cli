"""Natural-language date/time parser — mirrors src/utils/mcp/dateTimeParser.ts"""
from __future__ import annotations

import re
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Union

DateTimeParseResult = Union[Dict[str, str], Dict[str, Union[bool, str]]]


def looks_like_iso8601(input_str: str) -> bool:
    """Return True if *input_str* already looks like an ISO 8601 date or datetime.

    Matches ``YYYY-MM-DD`` optionally followed by ``T`` (full datetime).
    Used to decide whether to attempt natural-language parsing.
    """
    return bool(re.match(r'^\d{4}-\d{2}-\d{2}(T|$)', input_str.strip()))


# camelCase alias
looksLikeISO8601 = looks_like_iso8601


async def parse_natural_language_date_time(
    input_str: str,
    fmt: str,
    signal: object = None,
) -> DateTimeParseResult:
    """Parse a natural-language date/time string into ISO 8601 format.

    This implementation uses the dateparser library when available,
    falling back to a best-effort heuristic so that the function always
    returns a usable result without requiring a network call to an LLM.

    Parameters
    ----------
    input_str:
        Natural-language expression, e.g. ``"tomorrow at 3pm"``.
    fmt:
        ``"date"`` (YYYY-MM-DD only) or ``"date-time"`` (full ISO 8601 with
        timezone offset).
    signal:
        Ignored in the Python port (no async cancellation concept needed).

    Returns
    -------
    ``{"success": True, "value": "<iso-string>"}`` or
    ``{"success": False, "error": "<message>"}``.
    """
    stripped = input_str.strip()
    if not stripped:
        return {"success": False, "error": "Unable to parse date/time from input"}

    # If already ISO 8601, return as-is after light validation
    if looks_like_iso8601(stripped):
        return {"success": True, "value": stripped}

    # Try dateparser if installed
    try:
        import dateparser  # type: ignore[import]

        settings: dict = {"RETURN_AS_TIMEZONE_AWARE": True, "PREFER_FUTURE_DATES": True}
        parsed = dateparser.parse(stripped, settings=settings)
        if parsed is None:
            return {"success": False, "error": "Unable to parse date/time from input"}

        if fmt == "date":
            return {"success": True, "value": parsed.strftime("%Y-%m-%d")}
        else:
            # Full ISO 8601 with UTC offset
            offset = parsed.utcoffset()
            total_seconds = int(offset.total_seconds()) if offset else 0
            sign = "+" if total_seconds >= 0 else "-"
            total_seconds = abs(total_seconds)
            tz_hours, tz_mins = divmod(total_seconds // 60, 60)
            tz_str = f"{sign}{tz_hours:02d}:{tz_mins:02d}"
            return {"success": True, "value": parsed.strftime(f"%Y-%m-%dT%H:%M:%S{tz_str}")}
    except ImportError:
        pass

    # Minimal heuristic fallback for common relative expressions
    now = datetime.now(timezone.utc)
    lower = stripped.lower()

    _offset: timedelta | None = None
    if lower in ("today", "now"):
        _offset = timedelta(0)
    elif lower == "tomorrow":
        _offset = timedelta(days=1)
    elif lower == "yesterday":
        _offset = timedelta(days=-1)
    elif re.match(r'^in\s+(\d+)\s+hour', lower):
        m = re.match(r'^in\s+(\d+)\s+hour', lower)
        _offset = timedelta(hours=int(m.group(1)))  # type: ignore[union-attr]
    elif re.match(r'^in\s+(\d+)\s+day', lower):
        m = re.match(r'^in\s+(\d+)\s+day', lower)
        _offset = timedelta(days=int(m.group(1)))  # type: ignore[union-attr]

    if _offset is not None:
        target = now + _offset
        if fmt == "date":
            return {"success": True, "value": target.strftime("%Y-%m-%d")}
        return {"success": True, "value": target.strftime("%Y-%m-%dT%H:%M:%S+00:00")}

    return {"success": False, "error": "Unable to parse date/time from input"}


# camelCase alias
parseNaturalLanguageDateTime = parse_natural_language_date_time

