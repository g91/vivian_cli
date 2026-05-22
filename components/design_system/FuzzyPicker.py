"""FuzzyPicker component — functional port of src/components/design-system/FuzzyPicker.tsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Generic, TypeVar

from ...hooks.useSearchInput import KeyboardEvent, useSearchInput
from ...ink.hooks.use_terminal_focus import useTerminalFocus
from ...ink.stringWidth import stringWidth
from ..SearchBox import SearchBox
from .Byline import Byline
from .KeyboardShortcutHint import KeyboardShortcutHint
from .ListItem import ListItem
from .Pane import Pane

T = TypeVar("T")

DEFAULT_VISIBLE = 8
CHROME_ROWS = 10
MIN_VISIBLE = 2


def _clamp(value: int, minimum: int, maximum: int) -> int:
    if maximum < minimum:
        return minimum
    return max(minimum, min(value, maximum))


def _coerce_lines(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    render_lines = getattr(value, "render_lines", None)
    if callable(render_lines):
        return [str(item) for item in render_lines()]
    return [str(value)]


def firstWord(s: str) -> str:
    index = s.find(" ")
    return s if index == -1 else s[:index]


@dataclass(slots=True)
class PickerAction(Generic[T]):
    action: str
    handler: Callable[[T], None]


@dataclass(slots=True)
class FuzzyPicker(Generic[T]):
    title: str
    items: list[T]
    getKey: Callable[[T], str]
    renderItem: Callable[[T, bool], Any]
    onQueryChange: Callable[[str], None]
    onSelect: Callable[[T], None]
    onCancel: Callable[[], None]
    placeholder: str = "Type to search..."
    initialQuery: str = ""
    renderPreview: Callable[[T], Any] | None = None
    previewPosition: str = "bottom"
    visibleCount: int = DEFAULT_VISIBLE
    direction: str = "down"
    onTab: PickerAction[T] | None = None
    onShiftTab: PickerAction[T] | None = None
    onFocus: Callable[[T | None], None] | None = None
    emptyMessage: str | Callable[[str], str] = "No results"
    matchLabel: str | None = None
    selectAction: str = "select"
    extraHints: Any = None
    rows: int = 24
    columns: int = 80
    focusedIndex: int = field(default=0, init=False)
    _search_state: dict[str, Any] = field(init=False)

    def __post_init__(self) -> None:
        self._search_state = useSearchInput(
            isActive=True,
            onExit=lambda: None,
            onCancel=self.onCancel,
            initialQuery=self.initialQuery,
            backspaceExitsOnEmpty=False,
        )
        self.onQueryChange(self.query)
        self._notify_focus()

    @property
    def query(self) -> str:
        return str(self._search_state["_state"]["query"])

    @property
    def cursorOffset(self) -> int:
        return int(self._search_state["_state"]["cursorOffset"])

    def _visible_count(self) -> int:
        extra = 1 if self.matchLabel else 0
        return max(MIN_VISIBLE, min(self.visibleCount, self.rows - CHROME_ROWS - extra))

    def _notify_focus(self) -> None:
        if self.onFocus is None:
            return
        focused = self.items[self.focusedIndex] if 0 <= self.focusedIndex < len(self.items) else None
        self.onFocus(focused)

    def setItems(self, items: list[T]) -> None:
        self.items = items
        self.focusedIndex = _clamp(self.focusedIndex, 0, len(self.items) - 1)
        self._notify_focus()

    def setQuery(self, query: str) -> None:
        self._search_state["setQuery"](query)
        self.focusedIndex = 0
        self.onQueryChange(self.query)
        self._notify_focus()

    def step(self, delta: int) -> None:
        self.focusedIndex = _clamp(self.focusedIndex + delta, 0, len(self.items) - 1)
        self._notify_focus()

    def handleKeyDown(self, event: KeyboardEvent) -> None:
        if event.key == "up" or (event.ctrl and event.key == "p"):
            self.step(1 if self.direction == "up" else -1)
            return
        if event.key == "down" or (event.ctrl and event.key == "n"):
            self.step(-1 if self.direction == "up" else 1)
            return
        if event.key == "return":
            selected = self.items[self.focusedIndex] if self.items else None
            if selected is not None:
                self.onSelect(selected)
            return
        if event.key == "tab":
            selected = self.items[self.focusedIndex] if self.items else None
            if selected is None:
                return
            action = self.onShiftTab if getattr(event, "shift", False) else None
            if action is None:
                action = self.onTab
            if action is None:
                self.onSelect(selected)
            else:
                action.handler(selected)
            return
        self._search_state["handleKeyDown"](event)
        self.onQueryChange(self.query)
        self.focusedIndex = 0
        self._notify_focus()

    def _window(self) -> tuple[int, list[T]]:
        visible_count = self._visible_count()
        window_start = _clamp(self.focusedIndex - visible_count + 1, 0, len(self.items) - visible_count)
        return window_start, self.items[window_start : window_start + visible_count]

    def _render_list(self, visible: list[T], window_start: int) -> list[str]:
        visible_count = self._visible_count()
        if not visible:
            empty_text = self.emptyMessage(self.query) if callable(self.emptyMessage) else self.emptyMessage
            lines = [empty_text]
            while len(lines) < visible_count:
                lines.append("")
            return lines

        rows: list[str] = []
        for index, item in enumerate(visible):
            actual_index = window_start + index
            is_focused = actual_index == self.focusedIndex
            at_low_edge = index == 0 and window_start > 0
            at_high_edge = index == len(visible) - 1 and window_start + visible_count < len(self.items)
            rendered = self.renderItem(item, is_focused)
            item_lines = ListItem(
                isFocused=is_focused,
                showScrollUp=(at_high_edge if self.direction == "up" else at_low_edge),
                showScrollDown=(at_low_edge if self.direction == "up" else at_high_edge),
                styled=False,
                children=" ".join(_coerce_lines(rendered)) if _coerce_lines(rendered) else "",
            ).render_lines()
            rows.extend(item_lines)

        if self.direction == "up":
            rows = list(reversed(rows))
        return rows[:visible_count]

    def render_lines(self) -> list[str]:
        compact = self.columns < 120
        window_start, visible = self._window()
        visible_count = self._visible_count()
        focused = self.items[self.focusedIndex] if self.items and self.focusedIndex < len(self.items) else None
        preview_lines = _coerce_lines(self.renderPreview(focused)) if self.renderPreview and focused is not None else []
        list_lines = self._render_list(visible, window_start)
        if self.matchLabel:
            list_lines.append(self.matchLabel)
        if preview_lines and self.previewPosition == "right":
            left_width = max((stringWidth(line) for line in list_lines), default=0)
            combined: list[str] = []
            max_height = max(len(list_lines), max(visible_count, len(preview_lines)))
            for index in range(max_height):
                left = list_lines[index] if index < len(list_lines) else ""
                right = preview_lines[index] if index < len(preview_lines) else ""
                combined.append(f"{left.ljust(left_width)}  {right}".rstrip())
            list_lines = combined
        elif preview_lines:
            list_lines.extend(preview_lines)

        search_box = SearchBox(
            query=self.query,
            cursorOffset=self.cursorOffset,
            placeholder=self.placeholder,
            isFocused=True,
            isTerminalFocused=useTerminalFocus(),
        ).render_lines()

        hints = [
            KeyboardShortcutHint(shortcut="↑/↓", action=("nav" if compact else "navigate")),
            KeyboardShortcutHint(shortcut="Enter", action=(firstWord(self.selectAction) if compact else self.selectAction)),
        ]
        if self.onTab is not None:
            hints.append(KeyboardShortcutHint(shortcut="Tab", action=self.onTab.action))
        if self.onShiftTab is not None and not compact:
            hints.append(KeyboardShortcutHint(shortcut="shift+tab", action=self.onShiftTab.action))
        hints.append(KeyboardShortcutHint(shortcut="Esc", action="cancel"))
        if self.extraHints not in (None, False, ""):
            hints.extend(_coerce_lines(self.extraHints))

        lines = [self.title]
        if self.direction != "up":
            lines.extend(search_box)
        lines.extend(list_lines)
        if self.direction == "up":
            lines.extend(search_box)
        byline = Byline(hints)
        if byline:
            lines.append(byline)
        return Pane(children=lines, color="permission").render_lines()


__all__ = ["FuzzyPicker", "PickerAction", "firstWord"]