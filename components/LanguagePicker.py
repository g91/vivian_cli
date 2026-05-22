"""Language picker component — minimal port of src/components/LanguagePicker.tsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..keybindings.useKeybinding import useKeybinding
from .TextInput import TextInput


POINTER = "❯"
ELLIPSIS = "..."


@dataclass
class LanguagePicker:
    initialLanguage: str | None
    onComplete: Callable[[str | None], None]
    onCancel: Callable[[], None]
    language: str | None = field(init=False)
    cursorOffset: int = field(init=False)
    input: TextInput = field(init=False)

    def __post_init__(self) -> None:
        self.language = self.initialLanguage
        self.cursorOffset = len(self.initialLanguage or "")
        useKeybinding("confirm:no", self.onCancel, {"context": "Settings"})
        self.input = TextInput(
            value=self.language or "",
            onChange=self._handle_change,
            onSubmit=lambda _value: self.handleSubmit(),
            onExit=self.onCancel,
            focus=True,
            showCursor=True,
            placeholder=f"e.g., Japanese, 日本語, Español{ELLIPSIS}",
            columns=60,
            cursorOffset=self.cursorOffset,
            onChangeCursorOffset=self._handle_cursor_change,
            multiline=False,
        )

    def _handle_change(self, value: str) -> None:
        self.language = value
        self.input.value = value

    def _handle_cursor_change(self, offset: int) -> None:
        self.cursorOffset = offset
        self.input.cursorOffset = offset

    def handleSubmit(self) -> None:
        trimmed = self.language.strip() if self.language is not None else ""
        self.onComplete(trimmed or None)

    def handleKeyDown(self, event: Any) -> None:
        self.input.handleKeyDown(event)

    def render_lines(self) -> list[str]:
        input_line = self.input.render_lines()[0] if self.input.render_lines() else ""
        return [
            "Enter your preferred response and voice language:",
            f"{POINTER} {input_line}",
            "Leave empty for default (English)",
        ]


__all__ = ["LanguagePicker"]