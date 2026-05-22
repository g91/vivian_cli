"""Tabs component — simplified port of src/components/design-system/Tabs.tsx."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

from ...context.modalContext import useIsInsideModal, useModalScrollRef
from ...ink.components.TerminalSizeContext import getTerminalSizeContext
from ...ink.stringWidth import stringWidth


@dataclass(slots=True)
class _TabsContextValue:
    selectedTab: str | None = None
    width: int | None = None
    headerFocused: bool = False
    focusHeader: Callable[[], None] = lambda: None
    blurHeader: Callable[[], None] = lambda: None
    registerOptIn: Callable[[], Callable[[], None]] = lambda: (lambda: None)


_TABS_CONTEXT: ContextVar[_TabsContextValue] = ContextVar("tabs_context", default=_TabsContextValue())


def _coerce_lines(children: Any) -> list[str]:
    if children is None:
        return []
    if isinstance(children, str):
        return [children]
    if isinstance(children, list):
        return [str(line) for line in children]
    render_lines = getattr(children, "render_lines", None)
    if callable(render_lines):
        return [str(line) for line in render_lines()]
    return [str(children)]


@dataclass(slots=True)
class TabProps:
    title: str
    children: Any
    id: str | None = None


@dataclass(slots=True)
class Tabs:
    children: list[TabProps]
    title: str | None = None
    color: str | None = None
    defaultTab: str | None = None
    hidden: bool = False
    useFullWidth: bool = False
    selectedTab: str | None = None
    onTabChange: Callable[[str], None] | None = None
    banner: Any = None
    disableNavigation: bool = False
    initialHeaderFocused: bool = True
    contentHeight: int | None = None
    navFromContent: bool = False
    _internal_selected_index: int = field(default=0, init=False)
    _header_focused: bool = field(init=False)
    _opt_in_count: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        tab_ids = [tab.id or tab.title for tab in self.children]
        if self.defaultTab and self.defaultTab in tab_ids:
            self._internal_selected_index = tab_ids.index(self.defaultTab)
        self._header_focused = self.initialHeaderFocused

    @property
    def selected_tab_index(self) -> int:
        tab_ids = [tab.id or tab.title for tab in self.children]
        if self.selectedTab is not None and self.selectedTab in tab_ids:
            return tab_ids.index(self.selectedTab)
        return self._internal_selected_index

    def handleTabChange(self, offset: int) -> str:
        if not self.children:
            raise ValueError("Tabs requires at least one child tab")
        new_index = (self.selected_tab_index + len(self.children) + offset) % len(self.children)
        new_tab_id = self.children[new_index].id or self.children[new_index].title
        if self.onTabChange is not None:
            self.onTabChange(new_tab_id)
        else:
            self._internal_selected_index = new_index
        self._header_focused = True
        return new_tab_id

    def focusHeader(self) -> None:
        self._header_focused = True

    def blurHeader(self) -> None:
        self._header_focused = False

    def registerOptIn(self) -> Callable[[], None]:
        self._opt_in_count += 1

        def unregister() -> None:
            self._opt_in_count = max(0, self._opt_in_count - 1)

        return unregister

    def render_lines(self) -> list[str]:
        if not self.children:
            return []
        terminal_width = getTerminalSizeContext().columns
        tab_bits: list[str] = []
        for index, tab in enumerate(self.children):
            current = index == self.selected_tab_index
            label = f" {tab.title} "
            tab_bits.append(f"[{label}]" if current else label)
        header = " ".join(tab_bits)
        if self.title:
            header = f"{self.title} {header}"
        if self.useFullWidth:
            header = header + (" " * max(0, terminal_width - stringWidth(header)))
        current_tab = self.children[self.selected_tab_index]
        content_lines = _coerce_lines(current_tab.children)
        content_width = terminal_width if self.useFullWidth else None
        if self.contentHeight is not None:
            content_lines = content_lines[: self.contentHeight]
            while len(content_lines) < self.contentHeight:
                content_lines.append("")
        banner_lines = _coerce_lines(self.banner) if self.banner is not None else []
        margin_top = 0 if self.hidden else 1
        scroll_ref = useModalScrollRef()
        del scroll_ref
        token: Token[_TabsContextValue] | None = None
        try:
            token = _TABS_CONTEXT.set(
                _TabsContextValue(
                    selectedTab=current_tab.id or current_tab.title,
                    width=content_width,
                    headerFocused=self._header_focused,
                    focusHeader=self.focusHeader,
                    blurHeader=self.blurHeader,
                    registerOptIn=self.registerOptIn,
                )
            )
            content_lines = _coerce_lines(Tab(title=current_tab.title, id=current_tab.id, children=current_tab.children))
        finally:
            if token is not None:
                _TABS_CONTEXT.reset(token)
        lines: list[str] = []
        if not self.hidden:
            lines.append(header)
        lines.extend([""] * margin_top)
        lines.extend(banner_lines)
        lines.extend(content_lines)
        return lines


@dataclass(slots=True)
class Tab:
    title: str
    children: Any
    id: str | None = None

    def render_lines(self) -> list[str]:
        context = _TABS_CONTEXT.get()
        if context.selectedTab != (self.id or self.title):
            return []
        lines = _coerce_lines(self.children)
        if context.width is None or useIsInsideModal():
            return lines
        return [line[: context.width] for line in lines]


def useTabsWidth() -> int | None:
    return _TABS_CONTEXT.get().width


@contextmanager
def _tab_header_opt_in() -> Iterator[None]:
    unregister = _TABS_CONTEXT.get().registerOptIn()
    try:
        yield None
    finally:
        unregister()


def useTabHeaderFocus() -> dict[str, Any]:
    context = _TABS_CONTEXT.get()
    return {
        "headerFocused": context.headerFocused,
        "focusHeader": context.focusHeader,
        "blurHeader": context.blurHeader,
        "registerOptIn": _tab_header_opt_in,
    }


__all__ = ["Tab", "TabProps", "Tabs", "useTabHeaderFocus", "useTabsWidth"]