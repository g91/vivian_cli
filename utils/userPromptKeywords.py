"""User prompt keyword matchers — mirrors src/utils/userPromptKeywords.ts"""
from __future__ import annotations

import re

_NEGATIVE_PATTERN = re.compile(
    r"\b(wtf|wth|ffs|omfg|shit(ty|tiest)?|dumbass|horrible|awful|piss(ed|ing)? off"
    r"|piece of (shit|crap|junk)|what the (fuck|hell)|fuck(ing)? (broken|useless|terrible|awful|horrible)"
    r"|fuck you|screw (this|you)|so frustrating|this sucks|damn it)\b",
    re.IGNORECASE,
)

_KEEP_GOING_PATTERN = re.compile(r"\b(keep going|go on)\b", re.IGNORECASE)


def matches_negative_keyword(input: str) -> bool:
    """Return True if the input contains a negative/frustration keyword."""
    return bool(_NEGATIVE_PATTERN.search(input))


def matches_keep_going_keyword(input: str) -> bool:
    """Return True if the input means 'continue' or 'keep going'."""
    lower = input.lower().strip()
    if lower == "continue":
        return True
    return bool(_KEEP_GOING_PATTERN.search(lower))
