"""Port of src/ink/bidi.ts."""
from __future__ import annotations

import re
from typing import Any

ClusteredChar = dict[str, Any]

_RTL_RE = re.compile(
    "[\u0590-\u05FF\uFB1D-\uFB4F\u0600-\u06FF\u0750-\u077F"
    "\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\u0780-\u07BF\u0700-\u074F]"
)

_needs_bidi: bool | None = None


def _needsSoftwareBidi() -> bool:
    global _needs_bidi
    if _needs_bidi is None:
        import os, sys
        _needs_bidi = (
            sys.platform == "win32"
            or bool(os.environ.get("WT_SESSION"))
            or os.environ.get("TERM_PROGRAM") == "vscode"
        )
    return _needs_bidi


def _hasRTLCharacters(text: str) -> bool:
    return bool(_RTL_RE.search(text))


def reorderBidi(characters: list[ClusteredChar]) -> list[ClusteredChar]:
    if not _needsSoftwareBidi() or not characters:
        return characters

    plain_text = "".join(c.get("value", "") for c in characters)
    if not _hasRTLCharacters(plain_text):
        return characters

    # Simple bidi: detect RTL runs and reverse them
    levels = _get_bidi_levels(plain_text)

    char_levels: list[int] = []
    offset = 0
    for c in characters:
        val = c.get("value", "")
        char_levels.append(levels[offset] if offset < len(levels) else 0)
        offset += len(val)

    reordered = list(characters)
    max_level = max(char_levels) if char_levels else 0

    for level in range(max_level, 0, -1):
        i = 0
        while i < len(reordered):
            if char_levels[i] >= level:
                j = i + 1
                while j < len(reordered) and char_levels[j] >= level:
                    j += 1
                _reverse_range(reordered, i, j - 1)
                _reverse_range(char_levels, i, j - 1)
                i = j
            else:
                i += 1

    return reordered


def _get_bidi_levels(text: str) -> list[int]:
    """Simple RTL detection: mark RTL chars as level 1, LTR as 0."""
    levels = []
    for ch in text:
        if _hasRTLCharacters(ch):
            levels.append(1)
        else:
            levels.append(0)
    return levels


def _reverse_range(arr: list, start: int, end: int) -> None:
    while start < end:
        arr[start], arr[end] = arr[end], arr[start]
        start += 1
        end -= 1


reorder_bidi = reorderBidi
