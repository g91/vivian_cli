"""SearchBox component — minimal port of src/components/SearchBox.tsx."""

from __future__ import annotations

from dataclasses import dataclass


def _cursor_text(query: str, offset: int, placeholder: str, isTerminalFocused: bool) -> str:
    if query:
        if not isTerminalFocused:
            return query
        before = query[:offset]
        current = query[offset] if offset < len(query) else " "
        after = query[offset + 1 :] if offset < len(query) else ""
        return f"{before}[{current}]{after}"
    if not isTerminalFocused:
        return placeholder
    head = placeholder[:1] or " "
    tail = placeholder[1:]
    return f"[{head}]{tail}"


@dataclass(slots=True)
class SearchBox:
    query: str
    isFocused: bool
    isTerminalFocused: bool
    placeholder: str = "Search..."
    prefix: str = "/"
    width: int | str | None = None
    cursorOffset: int | None = None
    borderless: bool = False

    def render_lines(self) -> list[str]:
        offset = self.cursorOffset if self.cursorOffset is not None else len(self.query)
        body = _cursor_text(self.query, offset, self.placeholder, self.isTerminalFocused) if self.isFocused else (self.query or self.placeholder)
        prefix = self.prefix if self.isFocused else self.prefix.lower()
        line = f"{prefix} {body}"
        if self.borderless:
            return [line]
        border = "=" * max(len(line) + 2, 8)
        return [border, f" {line} ", border]


__all__ = ["SearchBox"]