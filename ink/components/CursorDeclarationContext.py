"""Port of src/ink/components/CursorDeclarationContext.ts."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Iterator

if TYPE_CHECKING:
    from ..dom import DOMElement


@dataclass(slots=True)
class CursorDeclaration:
    relativeX: int
    relativeY: int
    node: DOMElement


CursorDeclarationSetter = Callable[[CursorDeclaration | None, Any | None], None]


def _default_set_cursor(_declaration: CursorDeclaration | None, _clearIfNode: Any | None = None) -> None:
    return None


_CURSOR_DECLARATION_CONTEXT: ContextVar[CursorDeclarationSetter] = ContextVar(
    "ink_cursor_declaration_context",
    default=_default_set_cursor,
)


def getCursorDeclarationContext() -> CursorDeclarationSetter:
    return _CURSOR_DECLARATION_CONTEXT.get()


def setCursorDeclarationContext(setter: CursorDeclarationSetter) -> Token[CursorDeclarationSetter]:
    return _CURSOR_DECLARATION_CONTEXT.set(setter)


def resetCursorDeclarationContext(token: Token[CursorDeclarationSetter]) -> None:
    _CURSOR_DECLARATION_CONTEXT.reset(token)


@contextmanager
def provideCursorDeclarationContext(setter: CursorDeclarationSetter) -> Iterator[CursorDeclarationSetter]:
    token = setCursorDeclarationContext(setter)
    try:
        yield setter
    finally:
        resetCursorDeclarationContext(token)


CursorDeclarationContext = CursorDeclarationSetter
