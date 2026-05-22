"""Port of src/ink/components/StdinContext.ts."""
from __future__ import annotations

import sys
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any, Callable, Iterator, TextIO


@dataclass(slots=True)
class StdinContextProps:
    stdin: TextIO
    setRawMode: Callable[[bool], None]
    isRawModeSupported: bool
    internal_exitOnCtrlC: bool
    app: Any | None = None
    internal_eventEmitter: Any | None = None
    internal_querier: Any | None = None


def _default_set_raw_mode(_enabled: bool) -> None:
    return None


_STDIN_CONTEXT: ContextVar[StdinContextProps] = ContextVar(
    "ink_stdin_context",
    default=StdinContextProps(
        stdin=sys.stdin,
        setRawMode=_default_set_raw_mode,
        isRawModeSupported=bool(getattr(sys.stdin, "isatty", lambda: False)()),
        internal_exitOnCtrlC=True,
    ),
)


def getStdinContext() -> StdinContextProps:
    return _STDIN_CONTEXT.get()


def setStdinContext(context: StdinContextProps) -> Token[StdinContextProps]:
    return _STDIN_CONTEXT.set(context)


def resetStdinContext(token: Token[StdinContextProps]) -> None:
    _STDIN_CONTEXT.reset(token)


@contextmanager
def provideStdinContext(context: StdinContextProps) -> Iterator[StdinContextProps]:
    token = setStdinContext(context)
    try:
        yield context
    finally:
        resetStdinContext(token)


StdinContext = StdinContextProps
