"""Search input state helper mirroring src/hooks/useSearchInput.ts.

This is a runtime-agnostic port that preserves the edit and navigation
behavior without React dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class KeyboardEvent:
    key: str
    ctrl: bool = False
    meta: bool = False
    fn: bool = False

    def preventDefault(self) -> None:
        return None


def useSearchInput(
    *,
    isActive: bool,
    onExit: Callable[[], None],
    onCancel: Callable[[], None] | None = None,
    onExitUp: Callable[[], None] | None = None,
    columns: int | None = None,
    passthroughCtrlKeys: list[str] | None = None,
    initialQuery: str = "",
    backspaceExitsOnEmpty: bool = True,
) -> dict[str, Any]:
    passthroughCtrlKeys = passthroughCtrlKeys or []
    state = {"query": initialQuery, "cursorOffset": len(initialQuery)}

    def _set_query(q: str) -> None:
        state["query"] = q
        state["cursorOffset"] = len(q)

    def _insert(text: str) -> None:
        q = state["query"]
        c = state["cursorOffset"]
        state["query"] = q[:c] + text + q[c:]
        state["cursorOffset"] = c + len(text)

    def _backspace() -> None:
        q = state["query"]
        c = state["cursorOffset"]
        if c <= 0:
            return
        state["query"] = q[: c - 1] + q[c:]
        state["cursorOffset"] = c - 1

    def _delete() -> None:
        q = state["query"]
        c = state["cursorOffset"]
        if c >= len(q):
            return
        state["query"] = q[:c] + q[c + 1 :]

    def _move_left() -> None:
        state["cursorOffset"] = max(0, state["cursorOffset"] - 1)

    def _move_right() -> None:
        state["cursorOffset"] = min(len(state["query"]), state["cursorOffset"] + 1)

    def _delete_to_end() -> None:
        c = state["cursorOffset"]
        state["query"] = state["query"][:c]

    def _delete_to_start() -> None:
        c = state["cursorOffset"]
        state["query"] = state["query"][c:]
        state["cursorOffset"] = 0

    def _delete_word_before() -> None:
        q = state["query"]
        c = state["cursorOffset"]
        left = q[:c].rstrip()
        cut = len(left)
        while cut > 0 and not left[cut - 1].isspace():
            cut -= 1
        state["query"] = q[:cut] + q[c:]
        state["cursorOffset"] = cut

    def _delete_word_after() -> None:
        q = state["query"]
        c = state["cursorOffset"]
        right = q[c:].lstrip()
        consumed_ws = len(q[c:]) - len(right)
        i = 0
        while i < len(right) and not right[i].isspace():
            i += 1
        end = c + consumed_ws + i
        state["query"] = q[:c] + q[end:]

    def handleKeyDown(event: KeyboardEvent) -> None:
        if not isActive:
            return

        key = event.key.lower()
        q = state["query"]

        if event.ctrl and key in passthroughCtrlKeys:
            return

        if key in {"return", "down"}:
            onExit()
            return
        if key == "up":
            if onExitUp:
                onExitUp()
            return
        if key == "escape":
            if onCancel:
                onCancel()
            elif q:
                _set_query("")
            else:
                onExit()
            return

        if key == "backspace":
            if event.meta:
                _delete_word_before()
                return
            if not q:
                if backspaceExitsOnEmpty:
                    (onCancel or onExit)()
                return
            _backspace()
            return

        if key == "delete":
            _delete()
            return

        if key == "left":
            _move_left()
            return
        if key == "right":
            _move_right()
            return
        if key == "home":
            state["cursorOffset"] = 0
            return
        if key == "end":
            state["cursorOffset"] = len(state["query"])
            return

        if event.ctrl:
            if key == "a":
                state["cursorOffset"] = 0
                return
            if key == "e":
                state["cursorOffset"] = len(state["query"])
                return
            if key == "b":
                _move_left()
                return
            if key == "f":
                _move_right()
                return
            if key == "d":
                if not q:
                    (onCancel or onExit)()
                    return
                _delete()
                return
            if key == "h":
                if not q:
                    if backspaceExitsOnEmpty:
                        (onCancel or onExit)()
                    return
                _backspace()
                return
            if key == "k":
                _delete_to_end()
                return
            if key == "u":
                _delete_to_start()
                return
            if key == "w":
                _delete_word_before()
                return
            if key in {"g", "c"} and onCancel:
                onCancel()
                return
            return

        if event.meta:
            if key == "b":
                _delete_word_before()
                return
            if key == "d":
                _delete_word_after()
                return

        if key == "tab":
            return

        if len(event.key) >= 1:
            _insert(event.key)

    return {
        "query": state["query"],
        "setQuery": _set_query,
        "cursorOffset": state["cursorOffset"],
        "handleKeyDown": handleKeyDown,
        "_state": state,
    }


use_search_input = useSearchInput
