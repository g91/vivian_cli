"""Ask user question permission request — compact port of src/components/permissions/AskUserQuestionPermissionRequest/AskUserQuestionPermissionRequest.tsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..TextInput import TextInput
from .PermissionDialog import PermissionDialog


def _tool_value(tool_use_confirm: Any, name: str, default: Any = None) -> Any:
    if hasattr(tool_use_confirm, name):
        return getattr(tool_use_confirm, name)
    if isinstance(tool_use_confirm, dict):
        return tool_use_confirm.get(name, default)
    return default


def _input_data(tool_use_confirm: Any) -> dict[str, Any]:
    input_data = _tool_value(tool_use_confirm, "input", {}) or {}
    return input_data if isinstance(input_data, dict) else {}


def _options(tool_use_confirm: Any) -> list[dict[str, Any]]:
    raw_options = _input_data(tool_use_confirm).get("options") or []
    return [option for option in raw_options if isinstance(option, dict)]


def _default_focus_index(options: list[dict[str, Any]]) -> int:
    for index, option in enumerate(options):
        if option.get("recommended"):
            return index
    return 0


@dataclass
class AskUserQuestionPermissionRequest:
    toolUseConfirm: Any
    onDone: Callable[[], None]
    onReject: Callable[[], None]
    workerBadge: Any = None
    _focused_index: int = field(init=False, default=0)
    _selected_labels: set[str] = field(init=False, default_factory=set)
    _custom_input: str = field(init=False, default="")
    _custom_input_mode: bool = field(init=False, default=False)
    _custom_cursor: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self._focused_index = _default_focus_index(_options(self.toolUseConfirm))

    def _question(self) -> str:
        return str(_input_data(self.toolUseConfirm).get("question") or "Answer this question?")

    def _multi_select(self) -> bool:
        return bool(_input_data(self.toolUseConfirm).get("multiSelect", False))

    def _items(self) -> list[tuple[str, str]]:
        items = [("option", str(option.get("label") or "")) for option in _options(self.toolUseConfirm)]
        items.append(("other", "Other"))
        if self._multi_select():
            items.append(("submit", "Submit"))
        return items

    def _focused_item(self) -> tuple[str, str] | None:
        items = self._items()
        if not items:
            return None
        self._focused_index = max(0, min(self._focused_index, len(items) - 1))
        return items[self._focused_index]

    def _move(self, delta: int) -> None:
        items = self._items()
        if not items:
            return
        self._focused_index = (self._focused_index + delta) % len(items)

    def _selected_option_list(self) -> list[str]:
        return [
            str(option.get("label") or "")
            for option in _options(self.toolUseConfirm)
            if str(option.get("label") or "") in self._selected_labels
        ]

    def _submit(self, selected_options: list[str] | None = None, custom_input: str | None = None) -> None:
        updated_input = dict(_input_data(self.toolUseConfirm))
        updated_input["selectedOptions"] = list(selected_options if selected_options is not None else self._selected_option_list())
        updated_input["customInput"] = custom_input if custom_input is not None else self._custom_input.strip()
        on_allow = _tool_value(self.toolUseConfirm, "onAllow")
        if callable(on_allow):
            on_allow(updated_input, [])
        self.onDone()

    def _toggle_label(self, label: str) -> None:
        if label in self._selected_labels:
            self._selected_labels.remove(label)
        else:
            self._selected_labels.add(label)

    def _start_custom_input(self) -> None:
        self._custom_input_mode = True
        self._custom_cursor = len(self._custom_input)

    def _cancel(self) -> None:
        on_reject = _tool_value(self.toolUseConfirm, "onReject")
        if callable(on_reject):
            on_reject()
        self.onReject()
        self.onDone()

    def _set_custom_input(self, value: str) -> None:
        self._custom_input = value

    def _set_custom_cursor(self, value: int) -> None:
        self._custom_cursor = value

    def _submit_custom_input(self, value: str) -> None:
        self._custom_input = value
        self._custom_cursor = len(value)
        self._custom_input_mode = False
        if not self._multi_select():
            self._submit([], value.strip())

    def _exit_custom_input(self) -> None:
        self._custom_input_mode = False
        self._custom_cursor = len(self._custom_input)

    def handleKeyDown(self, event: Any) -> None:
        if self._custom_input_mode:
            TextInput(
                value=self._custom_input,
                onChange=self._set_custom_input,
                columns=120,
                cursorOffset=self._custom_cursor,
                onChangeCursorOffset=self._set_custom_cursor,
                placeholder="Type another answer",
                focus=True,
                showCursor=True,
                onSubmit=self._submit_custom_input,
                onExit=self._exit_custom_input,
            ).handleKeyDown(event)
            return
        key = str(getattr(event, "key", "")).lower()
        if key == "up":
            self._move(-1)
            return
        if key == "down":
            self._move(1)
            return
        if key == "escape":
            self._cancel()
            return
        if key == "space":
            focused = self._focused_item()
            if self._multi_select() and focused and focused[0] == "option":
                self._toggle_label(focused[1])
            return
        if key != "return":
            return
        focused = self._focused_item()
        if focused is None:
            return
        kind, value = focused
        if kind == "option":
            if self._multi_select():
                self._toggle_label(value)
            else:
                self._submit([value], self._custom_input.strip())
            return
        if kind == "other":
            self._start_custom_input()
            return
        if kind == "submit":
            self._submit()

    def _preview_lines(self) -> list[str]:
        if self._multi_select():
            return []
        focused = self._focused_item()
        if focused is None or focused[0] != "option":
            return []
        for option in _options(self.toolUseConfirm):
            if str(option.get("label") or "") == focused[1]:
                preview = str(option.get("preview") or "").strip()
                return ["Preview:", *preview.splitlines()] if preview else []
        return []

    def render_lines(self) -> list[str]:
        lines = [self._question(), ""]
        items = self._items()
        option_list = _options(self.toolUseConfirm)
        for index, (kind, value) in enumerate(items):
            focused = "❯" if index == self._focused_index else " "
            if kind == "option":
                if self._multi_select():
                    checked = "[x]" if value in self._selected_labels else "[ ]"
                    lines.append(f"{focused} {checked} {value}")
                else:
                    lines.append(f"{focused} {value}")
                description = str(option_list[index].get("description") or "").strip()
                if description:
                    lines.append(f"  {description}")
                continue
            if kind == "other":
                if self._custom_input_mode:
                    preview = TextInput(
                        value=self._custom_input,
                        onChange=lambda _value: None,
                        columns=120,
                        cursorOffset=self._custom_cursor,
                        onChangeCursorOffset=lambda _offset: None,
                        placeholder="Type another answer",
                        focus=True,
                        showCursor=True,
                    ).render_lines()[0]
                    lines.append(f"{focused} Other: {preview}")
                else:
                    suffix = f": {self._custom_input}" if self._custom_input else ""
                    lines.append(f"{focused} Other{suffix}")
                continue
            summary = ", ".join(self._selected_option_list()) or "no selections"
            custom_suffix = " + custom input" if self._custom_input.strip() else ""
            lines.append(f"{focused} Submit ({summary}{custom_suffix})")
        preview_lines = self._preview_lines()
        if preview_lines:
            lines.extend(["", *preview_lines])
        lines.append("")
        lines.append("Space to toggle selections · Enter to answer · Esc to cancel" if self._multi_select() else "Enter to answer · Esc to cancel")
        return PermissionDialog(title="Answer question", workerBadge=self.workerBadge, children=lines).render_lines()


__all__ = ["AskUserQuestionPermissionRequest"]