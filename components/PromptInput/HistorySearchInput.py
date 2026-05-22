"""History search input — minimal port of src/components/PromptInput/HistorySearchInput.tsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ...ink.stringWidth import stringWidth
from ..TextInput import TextInput


@dataclass
class HistorySearchInput:
    value: str
    onChange: Callable[[str], None]
    historyFailedMatch: bool
    input: TextInput = field(init=False)

    def __post_init__(self) -> None:
        self.input = TextInput(
            value=self.value,
            onChange=self._handle_change,
            cursorOffset=len(self.value),
            onChangeCursorOffset=self._ignore_cursor_change,
            columns=max(stringWidth(self.value) + 1, 1),
            focus=True,
            showCursor=True,
            multiline=False,
            dimColor=True,
        )

    def _handle_change(self, value: str) -> None:
        self.value = value
        self.onChange(value)
        self.input.value = value
        self.input.cursorOffset = len(value)
        self.input.columns = max(stringWidth(value) + 1, 1)

    def _ignore_cursor_change(self, _offset: int) -> None:
        self.input.cursorOffset = len(self.value)

    def handleKeyDown(self, event: Any) -> None:
        self.input.cursorOffset = len(self.value)
        self.input.columns = max(stringWidth(self.value) + 1, 1)
        self.input.handleKeyDown(event)
        self.input.cursorOffset = len(self.value)

    def render_lines(self) -> list[str]:
        label = "no matching prompt:" if self.historyFailedMatch else "search prompts:"
        self.input.value = self.value
        self.input.cursorOffset = len(self.value)
        self.input.columns = max(stringWidth(self.value) + 1, 1)
        rendered_input = self.input.render_lines()[0] if self.input.render_lines() else ""
        return [f"{label} {rendered_input}"]


__all__ = ["HistorySearchInput"]