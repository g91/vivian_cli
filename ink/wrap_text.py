"""Port of src/ink/wrap-text.ts."""
from __future__ import annotations

from .stringWidth import stringWidth
from .wrapAnsi import wrapAnsi

ELLIPSIS = "\u2026"


def _slice_fit(text: str, start: int, end: int) -> str:
    s = text[start:end]
    if stringWidth(s) > end - start:
        s = text[start:end - 1]
    return s


def _truncate(text: str, columns: int, position: str) -> str:
    if columns < 1:
        return ""
    if columns == 1:
        return ELLIPSIS

    length = stringWidth(text)
    if length <= columns:
        return text

    if position == "start":
        return ELLIPSIS + _slice_fit(text, length - columns + 1, length)
    if position == "middle":
        half = columns // 2
        return (
            _slice_fit(text, 0, half)
            + ELLIPSIS
            + _slice_fit(text, length - (columns - half) + 1, length)
        )
    return _slice_fit(text, 0, columns - 1) + ELLIPSIS


def wrapText(text: str, maxWidth: int, wrapType: str | None) -> str:
    if wrapType == "wrap":
        return wrapAnsi(text, maxWidth, hard=True, trim=False)
    if wrapType == "wrap-trim":
        return wrapAnsi(text, maxWidth, hard=True, trim=True)
    if wrapType and wrapType.startswith("truncate"):
        position = "end"
        if wrapType == "truncate-middle":
            position = "middle"
        elif wrapType == "truncate-start":
            position = "start"
        return _truncate(text, maxWidth, position)
    return text


wrap_text = wrapText
