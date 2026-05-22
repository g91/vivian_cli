"""Intl/locale utilities — mirrors src/utils/intl.ts"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Iterator, Optional


class _SegmentView:
    def __init__(self, segment: str):
        self.segment = segment


class _Segmenter:
    def __init__(self, granularity: str):
        self.granularity = granularity

    def segment(self, text: str) -> Iterator[_SegmentView]:
        if self.granularity == "word":
            for match in re.finditer(r"\S+|\s+", text):
                yield _SegmentView(match.group(0))
            return
        for cluster in _grapheme_clusters(text):
            yield _SegmentView(cluster)


class _RelativeTimeFormatter:
    def __init__(self, style: str, numeric: str):
        self.style = style
        self.numeric = numeric

    def format(self, value: float, unit: str) -> str:
        if self.numeric == "auto":
            if unit == "second" and value == 0:
                return "now"
            if unit == "day" and value == -1:
                return "yesterday"
            if unit == "day" and value == 1:
                return "tomorrow"

        amount = abs(int(value))
        label = unit if amount == 1 else f"{unit}s"
        body = f"{amount} {label}"
        if value > 0:
            return f"in {body}"
        return f"{body} ago"


def _grapheme_clusters(text: str) -> list[str]:
    """Approximate grapheme cluster splitting using unicodedata."""
    # Python's built-in doesn't have Intl.Segmenter; use grapheme package if available,
    # otherwise approximate by iterating codepoints and grouping combining chars.
    try:
        import grapheme as _grapheme  # type: ignore[import]
        return list(_grapheme.graphemes(text))
    except ImportError:
        pass
    clusters: list[str] = []
    current = ""
    for ch in text:
        if current and unicodedata.category(ch) in ("Mn", "Mc", "Me"):
            current += ch
        else:
            if current:
                clusters.append(current)
            current = ch
    if current:
        clusters.append(current)
    return clusters


def first_grapheme(text: str) -> str:
    """Return the first grapheme cluster in text, or '' if empty."""
    if not text:
        return ""
    clusters = _grapheme_clusters(text)
    return clusters[0] if clusters else ""


def last_grapheme(text: str) -> str:
    """Return the last grapheme cluster in text, or '' if empty."""
    if not text:
        return ""
    clusters = _grapheme_clusters(text)
    return clusters[-1] if clusters else ""


@lru_cache(maxsize=2)
def get_grapheme_segmenter() -> _Segmenter:
    return _Segmenter("grapheme")


@lru_cache(maxsize=2)
def get_word_segmenter() -> _Segmenter:
    return _Segmenter("word")


@lru_cache(maxsize=16)
def get_relative_time_format(style: str = "long", numeric: str = "always") -> object:
    """Return a cached relative-time formatter with a `.format(value, unit)` method."""
    return _RelativeTimeFormatter(style, numeric)


def format_relative_time(seconds: float) -> str:
    """Return a human-readable relative time string (e.g., '2 hours ago')."""
    abs_s = abs(seconds)
    future = seconds > 0

    if abs_s < 60:
        val, unit = int(abs_s), "second"
    elif abs_s < 3600:
        val, unit = int(abs_s / 60), "minute"
    elif abs_s < 86400:
        val, unit = int(abs_s / 3600), "hour"
    else:
        val, unit = int(abs_s / 86400), "day"

    plural = "s" if val != 1 else ""
    label = f"{val} {unit}{plural}"
    return f"in {label}" if future else f"{label} ago"


@lru_cache(maxsize=1)
def get_time_zone() -> str:
    """Return the system timezone name."""
    import datetime
    return str(datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo)


@lru_cache(maxsize=1)
def get_locale_language() -> Optional[str]:
    """Return the system locale language subtag (e.g. 'en')."""
    import locale
    lang, _ = locale.getlocale()
    if lang:
        return lang.split("_")[0].split("-")[0]
    return None


def get_system_locale_language() -> Optional[str]:
    return get_locale_language()


firstGrapheme = first_grapheme
lastGrapheme = last_grapheme
getGraphemeSegmenter = get_grapheme_segmenter
getWordSegmenter = get_word_segmenter
getRelativeTimeFormat = get_relative_time_format
formatRelativeTime = format_relative_time
getTimeZone = get_time_zone
getSystemLocaleLanguage = get_system_locale_language
