"""Port of src/hooks/renderPlaceholder.ts."""
from __future__ import annotations

from typing import Callable, Optional


def _dim(text: str) -> str:
    return text


def _inverse(text: str) -> str:
    return text


def renderPlaceholder(
    *,
    placeholder: Optional[str] = None,
    value: str,
    showCursor: bool = False,
    focus: bool = False,
    terminalFocus: bool = True,
    invert: Optional[Callable[[str], str]] = None,
    hidePlaceholderText: bool = False,
) -> dict:
    renderedPlaceholder: Optional[str] = None
    invert_fn = invert or _inverse

    if placeholder is not None:
        if hidePlaceholderText:
            renderedPlaceholder = invert_fn(' ') if (showCursor and focus and terminalFocus) else ''
        else:
            renderedPlaceholder = _dim(placeholder)
            if showCursor and focus and terminalFocus:
                renderedPlaceholder = (
                    invert_fn(placeholder[0]) + _dim(placeholder[1:])
                    if len(placeholder) > 0
                    else invert_fn(' ')
                )

    showPlaceholder = len(value) == 0 and bool(placeholder)
    return {
        'renderedPlaceholder': renderedPlaceholder,
        'showPlaceholder': showPlaceholder,
    }
