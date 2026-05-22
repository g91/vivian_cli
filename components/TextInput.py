"""Text input component — minimal port of src/components/TextInput.tsx."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


def _cursor_text(value: str, offset: int, placeholder: str, show_cursor: bool) -> str:
    if value:
        display = value
    else:
        display = placeholder

    if not show_cursor:
        return display

    if not value:
        head = display[:1] or " "
        tail = display[1:]
        return f"[{head}]{tail}"

    bounded_offset = max(0, min(offset, len(value)))
    current = value[bounded_offset] if bounded_offset < len(value) else " "
    before = value[:bounded_offset]
    after = value[bounded_offset + 1 :] if bounded_offset < len(value) else ""
    return f"{before}[{current}]{after}"


@dataclass
class TextInput:
    value: str
    onChange: Callable[[str], None]
    columns: int
    cursorOffset: int
    onChangeCursorOffset: Callable[[int], None]
    onHistoryUp: Callable[[], None] | None = None
    onHistoryDown: Callable[[], None] | None = None
    placeholder: str | None = None
    multiline: bool = True
    focus: bool = True
    mask: str | None = None
    showCursor: bool = False
    highlightPastedText: bool = False
    onSubmit: Callable[[str], None] | None = None
    onExit: Callable[[], None] | None = None
    onExitMessage: Callable[[bool, str | None], None] | None = None
    onHistoryReset: Callable[[], None] | None = None
    onClearInput: Callable[[], None] | None = None
    maxVisibleLines: int | None = None
    onImagePaste: Callable[[str, str | None, str | None, Any | None, str | None], None] | None = None
    onPaste: Callable[[str], None] | None = None
    onIsPastingChange: Callable[[bool], None] | None = None
    disableCursorMovementForUpDownKeys: bool = False
    disableEscapeDoublePress: bool = False
    argumentHint: str | None = None
    onUndo: Callable[[], None] | None = None
    dimColor: bool = False
    highlights: list[Any] | None = None
    placeholderElement: Any | None = None
    inlineGhostText: Any | None = None
    inputFilter: Callable[[str, Any], str] | None = None

    def _set_value(self, next_value: str) -> None:
        self.value = next_value
        self.onChange(next_value)

    def _set_cursor(self, next_offset: int) -> None:
        bounded = max(0, min(next_offset, len(self.value)))
        self.cursorOffset = bounded
        self.onChangeCursorOffset(bounded)

    def _insert(self, text: str) -> None:
        next_text = text
        if self.inputFilter is not None:
            next_text = self.inputFilter(text, None)
        if not next_text:
            return
        next_value = self.value[: self.cursorOffset] + next_text + self.value[self.cursorOffset :]
        self._set_value(next_value)
        self._set_cursor(self.cursorOffset + len(next_text))

    def _backspace(self) -> None:
        if self.cursorOffset <= 0:
            return
        next_value = self.value[: self.cursorOffset - 1] + self.value[self.cursorOffset :]
        self._set_value(next_value)
        self._set_cursor(self.cursorOffset - 1)

    def _delete(self) -> None:
        if self.cursorOffset >= len(self.value):
            return
        next_value = self.value[: self.cursorOffset] + self.value[self.cursorOffset + 1 :]
        self._set_value(next_value)
        self._set_cursor(self.cursorOffset)

    def handleKeyDown(self, event: Any) -> None:
        if not self.focus:
            return

        key = str(getattr(event, "key", "")).lower()
        ctrl = bool(getattr(event, "ctrl", False))
        meta = bool(getattr(event, "meta", False))

        if key == "return":
            if self.onSubmit is not None:
                self.onSubmit(self.value)
            return

        if key == "escape":
            if self.onExit is not None:
                self.onExit()
            return

        if key == "backspace":
            if not self.value and self.onExit is not None:
                self.onExit()
                return
            self._backspace()
            return

        if key == "delete":
            self._delete()
            return

        if key == "left":
            self._set_cursor(self.cursorOffset - 1)
            return

        if key == "right":
            self._set_cursor(self.cursorOffset + 1)
            return

        if key == "home" or (ctrl and key == "a"):
            self._set_cursor(0)
            return

        if key == "end" or (ctrl and key == "e"):
            self._set_cursor(len(self.value))
            return

        if key == "up" and self.onHistoryUp is not None:
            self.onHistoryUp()
            return

        if key == "down" and self.onHistoryDown is not None:
            self.onHistoryDown()
            return

        if ctrl or meta or key == "tab":
            return

        raw_key = str(getattr(event, "key", ""))
        if len(raw_key) == 1:
            self._insert(raw_key)

    def render_lines(self) -> list[str]:
        placeholder = self.placeholder or ""
        visible_value = self.value
        if self.mask is not None:
            visible_value = self.mask * len(self.value)
        body = _cursor_text(visible_value, self.cursorOffset, placeholder, self.showCursor and self.focus)
        line = body[: self.columns] if self.columns > 0 else body
        return [line]


__all__ = ["TextInput"]