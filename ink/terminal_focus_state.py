"""Port of src/ink/terminal-focus-state.ts."""
from __future__ import annotations

from typing import Callable, Literal

TerminalFocusState = Literal["focused", "blurred", "unknown"]

_focus_state: TerminalFocusState = "unknown"
_subscribers: set[Callable[[], None]] = set()


def setTerminalFocused(v: bool) -> None:
    global _focus_state
    _focus_state = "focused" if v else "blurred"
    for cb in list(_subscribers):
        cb()


def getTerminalFocused() -> bool:
    return _focus_state != "blurred"


def getTerminalFocusState() -> TerminalFocusState:
    return _focus_state


def subscribeTerminalFocus(cb: Callable[[], None]) -> Callable[[], None]:
    _subscribers.add(cb)
    def unsubscribe() -> None:
        _subscribers.discard(cb)
    return unsubscribe


def resetTerminalFocusState() -> None:
    global _focus_state
    _focus_state = "unknown"
    for cb in list(_subscribers):
        cb()


set_terminal_focused = setTerminalFocused
get_terminal_focused = getTerminalFocused
get_terminal_focus_state = getTerminalFocusState
subscribe_terminal_focus = subscribeTerminalFocus
reset_terminal_focus_state = resetTerminalFocusState
