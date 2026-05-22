"""Port of src/ink/components/TerminalSizeContext.tsx."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Iterator


@dataclass(slots=True)
class TerminalSize:
    columns: int
    rows: int


_TERMINAL_SIZE_CONTEXT: ContextVar[TerminalSize] = ContextVar(
    "ink_terminal_size_context",
    default=TerminalSize(columns=80, rows=24),
)


def getTerminalSizeContext() -> TerminalSize:
    return _TERMINAL_SIZE_CONTEXT.get()


def setTerminalSizeContext(size: TerminalSize) -> Token[TerminalSize]:
    return _TERMINAL_SIZE_CONTEXT.set(size)


def resetTerminalSizeContext(token: Token[TerminalSize]) -> None:
    _TERMINAL_SIZE_CONTEXT.reset(token)


@contextmanager
def provideTerminalSizeContext(size: TerminalSize) -> Iterator[TerminalSize]:
    token = setTerminalSizeContext(size)
    try:
        yield size
    finally:
        resetTerminalSizeContext(token)


TerminalSizeContext = TerminalSize
