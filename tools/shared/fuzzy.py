"""
Shared fuzzy matching — mirrors src/tools/shared/fuzzy.ts
"""
from __future__ import annotations
import difflib
from typing import List, Optional


def fuzzyFind(pattern: str, candidates: List[str], cutoff: float = 0.6) -> List[str]:
    """
    Find candidates that fuzzy-match the given pattern.
    Returns matches sorted by similarity (best first).
    """
    scores = []
    for candidate in candidates:
        ratio = difflib.SequenceMatcher(None, pattern.lower(), candidate.lower()).ratio()
        if ratio >= cutoff:
            scores.append((ratio, candidate))
    scores.sort(reverse=True, key=lambda x: x[0])
    return [c for _, c in scores]


def fuzzyMatch(pattern: str, text: str) -> bool:
    """Check if pattern fuzzy-matches text."""
    ratio = difflib.SequenceMatcher(None, pattern.lower(), text.lower()).ratio()
    return ratio >= 0.6
