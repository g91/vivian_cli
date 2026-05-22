"""Modal context helpers — minimal port of src/context/modalContext.tsx."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any, Iterator


_INSIDE_MODAL: ContextVar[bool] = ContextVar("inside_modal", default=False)
_MODAL_SCROLL_REF: ContextVar[Any] = ContextVar("modal_scroll_ref", default=None)


def useIsInsideModal() -> bool:
    return _INSIDE_MODAL.get()


def useModalScrollRef() -> Any:
    return _MODAL_SCROLL_REF.get()


@contextmanager
def provideModalContext(*, inside: bool = True, scrollRef: Any = None) -> Iterator[None]:
    inside_token: Token[bool] = _INSIDE_MODAL.set(inside)
    scroll_token: Token[Any] = _MODAL_SCROLL_REF.set(scrollRef)
    try:
        yield None
    finally:
        _INSIDE_MODAL.reset(inside_token)
        _MODAL_SCROLL_REF.reset(scroll_token)


__all__ = ["provideModalContext", "useIsInsideModal", "useModalScrollRef"]