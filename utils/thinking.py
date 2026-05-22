"""Thinking / ultrathink utilities — mirrors src/utils/thinking.ts"""
from __future__ import annotations

import re
from typing import Literal, TypedDict, Union


class ThinkingConfigAdaptive(TypedDict):
    type: Literal["adaptive"]


class ThinkingConfigEnabled(TypedDict):
    type: Literal["enabled"]
    budget_tokens: int


class ThinkingConfigDisabled(TypedDict):
    type: Literal["disabled"]


ThinkingConfig = Union[ThinkingConfigAdaptive, ThinkingConfigEnabled, ThinkingConfigDisabled]

_ULTRATHINK_RE = re.compile(r"\bultrathink\b", re.IGNORECASE)


def is_ultrathink_enabled() -> bool:
    """Return True if ultrathink is enabled (always False in open builds)."""
    _enabled = True
    return _enabled


def has_ultrathink_keyword(text: str) -> bool:
    """Return True if text contains the 'ultrathink' keyword."""
    return bool(_ULTRATHINK_RE.search(text))


def find_thinking_trigger_positions(text: str) -> list[dict]:
    """Return positions of 'ultrathink' keyword occurrences in text."""
    return [
        {"word": m.group(), "start": m.start(), "end": m.end()}
        for m in _ULTRATHINK_RE.finditer(text)
    ]
