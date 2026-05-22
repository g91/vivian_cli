"""Port of src/ink/components/TerminalFocusContext.tsx."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator

from ..terminal_focus_state import getTerminalFocused


_TERMINAL_FOCUS_CONTEXT: ContextVar[bool] = ContextVar(
    "ink_terminal_focus_context",
    default=getTerminalFocused(),
)


def getTerminalFocusContext() -> bool:
    return _TERMINAL_FOCUS_CONTEXT.get()


def setTerminalFocusContext(focused: bool) -> Token[bool]:
    return _TERMINAL_FOCUS_CONTEXT.set(focused)


def resetTerminalFocusContext(token: Token[bool]) -> None:
    _TERMINAL_FOCUS_CONTEXT.reset(token)


@contextmanager
def TerminalFocusProvider(focused: bool | None = None) -> Iterator[bool]:
    value = getTerminalFocused() if focused is None else focused
    token = setTerminalFocusContext(value)
    try:
        yield value
    finally:
        resetTerminalFocusContext(token)
