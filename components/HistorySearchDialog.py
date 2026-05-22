"""HistorySearchDialog component — functional port of src/components/HistorySearchDialog.tsx."""

from __future__ import annotations

import asyncio
import inspect
import math
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from ..ink.wrapAnsi import wrapAnsi
from ..services.analytics.index import logEvent
from ..utils.history import TimestampedHistoryEntry, getTimestampedHistory
from .design_system.FuzzyPicker import FuzzyPicker

PREVIEW_ROWS = 6
AGE_WIDTH = 8


def formatRelativeTimeAgo(value: datetime) -> str:
    delta = max(0, int(time.time() - value.timestamp()))
    if delta < 60:
        return "now"
    if delta < 3600:
        return f"{delta // 60}m"
    if delta < 86400:
        return f"{delta // 3600}h"
    if delta < 86400 * 30:
        return f"{delta // 86400}d"
    return f"{delta // (86400 * 30)}mo"


def truncateToWidth(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[: width - 1] + "..."[:1]


def _is_subsequence(text: str, query: str) -> bool:
    query_index = 0
    for char in text:
        if query_index < len(query) and char == query[query_index]:
            query_index += 1
    return query_index == len(query)


async def _collect_history_items() -> list["HistorySearchItem"]:
    loaded: list[HistorySearchItem] = []
    async for entry in getTimestampedHistory():
        display = entry.display
        first_line = display.splitlines()[0] if display else ""
        age = formatRelativeTimeAgo(datetime.fromtimestamp(entry.timestamp))
        loaded.append(
            HistorySearchItem(
                entry=entry,
                display=display,
                lower=display.lower(),
                firstLine=first_line,
                age=age + (" " * max(0, AGE_WIDTH - len(age))),
            )
        )
    return loaded


def _load_history_items_sync() -> list["HistorySearchItem"] | None:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_collect_history_items())
    return None


def _resolve_entry_sync(entry: TimestampedHistoryEntry) -> Any:
    resolved = entry.resolve()
    if inspect.isawaitable(resolved):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(resolved)
        return None
    return resolved


@dataclass(slots=True)
class HistorySearchItem:
    entry: TimestampedHistoryEntry
    display: str
    lower: str
    firstLine: str
    age: str


@dataclass(slots=True)
class HistorySearchDialog:
    onSelect: Callable[[Any], None]
    onCancel: Callable[[], None]
    initialQuery: str | None = None
    items: list[HistorySearchItem] | None = field(default=None, init=False)
    query: str = field(default="", init=False)
    picker: FuzzyPicker[HistorySearchItem] | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.query = self.initialQuery or ""
        self.items = _load_history_items_sync()
        columns = shutil.get_terminal_size().columns
        preview_on_right = columns >= 100
        list_width = math.floor((columns - 6) * 0.5) if preview_on_right else columns - 6
        row_width = max(20, list_width - AGE_WIDTH - 1)
        preview_width = max(20, columns - list_width - 12) if preview_on_right else max(20, columns - 10)

        self.picker = FuzzyPicker(
            title="Search prompts",
            placeholder="Filter history...",
            initialQuery=self.initialQuery or "",
            items=self._filtered_items(),
            getKey=lambda item: str(item.entry.timestamp),
            onQueryChange=self._handle_query_change,
            onSelect=self._handle_select,
            onCancel=self.onCancel,
            emptyMessage=lambda query: "Loading..." if self.items is None else ("No matching prompts" if query else "No history yet"),
            selectAction="use",
            direction="up",
            previewPosition=("right" if preview_on_right else "bottom"),
            renderItem=lambda item, isFocused: f"{item.age} {truncateToWidth(item.firstLine, row_width)}",
            renderPreview=lambda item: self._render_preview(item, preview_width),
        )

    def _filtered_items(self) -> list[HistorySearchItem]:
        if self.items is None:
            return []
        normalized = self.query.strip().lower()
        if not normalized:
            return self.items
        exact: list[HistorySearchItem] = []
        fuzzy: list[HistorySearchItem] = []
        for item in self.items:
            if normalized in item.lower:
                exact.append(item)
            elif _is_subsequence(item.lower, normalized):
                fuzzy.append(item)
        return exact + fuzzy

    def _handle_query_change(self, query: str) -> None:
        self.query = query
        if self.picker is None:
            return
        self.picker.items = self._filtered_items()
        self.picker.focusedIndex = 0

    def _handle_select(self, item: HistorySearchItem) -> None:
        logEvent(
            "tengu_history_picker_select",
            {"result_count": len(self._filtered_items()), "query_length": len(self.query)},
        )
        resolved = _resolve_entry_sync(item.entry)
        if resolved is not None:
            self.onSelect(resolved)

    def _render_preview(self, item: HistorySearchItem, preview_width: int) -> list[str]:
        wrapped = [line for line in wrapAnsi(item.display, preview_width, hard=True).split("\n") if line.strip()]
        overflow = len(wrapped) > PREVIEW_ROWS
        shown = wrapped[: PREVIEW_ROWS - 1] if overflow else wrapped[:PREVIEW_ROWS]
        more = len(wrapped) - len(shown)
        lines = [f"| {line}" for line in shown]
        if more > 0:
            lines.append(f"| ... +{more} more lines")
        return lines

    async def load_async(self) -> None:
        self.items = await _collect_history_items()
        self._handle_query_change(self.query)

    def render_lines(self) -> list[str]:
        if self.picker is None:
            return []
        return self.picker.render_lines()

    def handleKeyDown(self, event: Any) -> None:
        if self.picker is None:
            return
        self.picker.handleKeyDown(event)


__all__ = [
    "HistorySearchDialog",
    "HistorySearchItem",
    "formatRelativeTimeAgo",
    "truncateToWidth",
]