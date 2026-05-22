"""Port of src/ink/components/AppContext.ts."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Callable, Iterator


@dataclass(slots=True)
class AppContextProps:
    exit: Callable[[Exception | None], None]


def _default_exit(error: Exception | None = None) -> None:
    if error is not None:
        raise error


_APP_CONTEXT: ContextVar[AppContextProps] = ContextVar(
    "ink_app_context",
    default=AppContextProps(exit=_default_exit),
)


def getAppContext() -> AppContextProps:
    return _APP_CONTEXT.get()


def setAppContext(context: AppContextProps) -> Token[AppContextProps]:
    return _APP_CONTEXT.set(context)


def resetAppContext(token: Token[AppContextProps]) -> None:
    _APP_CONTEXT.reset(token)


@contextmanager
def provideAppContext(context: AppContextProps) -> Iterator[AppContextProps]:
    token = setAppContext(context)
    try:
        yield context
    finally:
        resetAppContext(token)


AppContext = AppContextProps
