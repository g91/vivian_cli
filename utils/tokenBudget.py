"""Port of src/utils/tokenBudget.ts"""
from __future__ import annotations
import re
from typing import Dict, List, Optional

_SHORTHAND_START_RE = re.compile(r"^\s*\+(\d+(?:\.\d+)?)\s*(k|m|b)\b", re.IGNORECASE)
_SHORTHAND_END_RE = re.compile(r"\s\+(\d+(?:\.\d+)?)\s*(k|m|b)\s*[.!?]?\s*$", re.IGNORECASE)
_VERBOSE_RE = re.compile(r"\b(?:use|spend)\s+(\d+(?:\.\d+)?)\s*(k|m|b)\s*tokens?\b", re.IGNORECASE)

_MULTIPLIERS: Dict[str, int] = {
    "k": 1_000,
    "m": 1_000_000,
    "b": 1_000_000_000,
}


def _parseBudgetMatch(value: str, suffix: str) -> float:
    return float(value) * _MULTIPLIERS[suffix.lower()]


def parseTokenBudget(text: str) -> Optional[float]:
    m = _SHORTHAND_START_RE.match(text)
    if m:
        return _parseBudgetMatch(m.group(1), m.group(2))
    m = _SHORTHAND_END_RE.search(text)
    if m:
        return _parseBudgetMatch(m.group(1), m.group(2))
    m = _VERBOSE_RE.search(text)
    if m:
        return _parseBudgetMatch(m.group(1), m.group(2))
    return None


def findTokenBudgetPositions(text: str) -> List[Dict[str, int]]:
    positions = []

    m = _SHORTHAND_START_RE.match(text)
    if m:
        offset = m.start() + len(m.group(0)) - len(m.group(0).lstrip())
        positions.append({"start": offset, "end": m.start() + len(m.group(0))})

    m = _SHORTHAND_END_RE.search(text)
    if m:
        end_start = m.start() + 1  # +1: regex includes leading whitespace
        already_covered = any(p["start"] <= end_start < p["end"] for p in positions)
        if not already_covered:
            positions.append({"start": end_start, "end": m.start() + len(m.group(0))})

    for match in _VERBOSE_RE.finditer(text):
        positions.append({"start": match.start(), "end": match.start() + len(match.group(0))})

    return positions


def getBudgetContinuationMessage(pct: float, turnTokens: int, budget: int) -> str:
    def fmt(n: int) -> str:
        return f"{n:,}"
    return (
        f"Stopped at {pct}% of token target ({fmt(turnTokens)} / {fmt(budget)}). "
        "Keep working \u2014 do not summarize."
    )
