"""Memory age helpers — mirrors src/memdir/memoryAge.ts."""
from __future__ import annotations

import time


def memory_age_days(mtime_ms: float) -> int:
    now_ms = time.time() * 1000
    return int((now_ms - mtime_ms) / 86_400_000)


def memory_age(mtime_ms: float) -> str:
    days = memory_age_days(mtime_ms)
    if days == 0:
        return "today"
    if days == 1:
        return "yesterday"
    return f"{days} days ago"


def memory_freshness_text(mtime_ms: float) -> str:
    days = memory_age_days(mtime_ms)
    if days == 0:
        return "very fresh (written today)"
    if days <= 7:
        return f"recent ({days}d old)"
    if days <= 30:
        return f"moderate ({days}d old)"
    if days <= 90:
        return f"older ({days}d old)"
    return f"stale ({days}d old)"


def memory_freshness_note(mtime_ms: float) -> str:
    text = memory_freshness_text(mtime_ms)
    return f"<system-reminder>Memory freshness: {text}</system-reminder>"
