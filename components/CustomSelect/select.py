"""Select component — compact port of src/components/CustomSelect/select.tsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Generic, TypeVar

from ..TextInput import TextInput


T = TypeVar("T")


@dataclass(slots=True)
class OptionWithDescription(Generic[T]):
    label: Any
    value: T
    description: str | None = None
    dimDescription: bool = False
    disabled: bool = False
    type: str = "text"
    onChange: Callable[[str], None] | None = None
    placeholder: str | None = None
    initialValue: str | None = None
    allowEmptySubmitToCancel: bool = False
    showLabelWithValue: bool = False
    labelValueSeparator: str | None = None
    resetCursorOnUpdate: bool = False


def _coerce_options(options: list[OptionWithDescription[T] | dict[str, Any]]) -> list[OptionWithDescription[T]]:
    coerced: list[OptionWithDescription[T]] = []
    for option in options:
        if isinstance(option, OptionWithDescription):
            coerced.append(option)
            continue
        coerced.append(
            OptionWithDescription(
                label=option.get("label", ""),
                value=option.get("value"),
                description=option.get("description"),
                dimDescription=bool(option.get("dimDescription", False)),
                disabled=bool(option.get("disabled", False)),
                type=str(option.get("type", "text")),
                onChange=option.get("onChange"),
                placeholder=option.get("placeholder"),
                initialValue=option.get("initialValue"),
                allowEmptySubmitToCancel=bool(option.get("allowEmptySubmitToCancel", False)),
                showLabelWithValue=bool(option.get("showLabelWithValue", False)),
                labelValueSeparator=option.get("labelValueSeparator"),
                resetCursorOnUpdate=bool(option.get("resetCursorOnUpdate", False)),
            )
        )
    return coerced


def _find_index_by_value(options: list[OptionWithDescription[T]], value: T | None) -> int | None:
    if value is None:
        return None
    for index, option in enumerate(options):
        if option.value == value:
            return index
    return None


def _next_enabled(options: list[OptionWithDescription[T]], start: int, step: int) -> int:
    if not options:
        return 0
    index = start
    for _ in range(len(options)):
        if not options[index].disabled:
            return index
        index = (index + step) % len(options)
    return start


@dataclass
class Select(Generic[T]):
    options: list[OptionWithDescription[T] | dict[str, Any]]
    isDisabled: bool = False
    disableSelection: bool = False
    hideIndexes: bool = False
    visibleOptionCount: int = 5
    highlightText: str | None = None
    defaultValue: T | None = None
    onCancel: Callable[[], None] | None = None
    onChange: Callable[[T], None] | None = None
    onFocus: Callable[[T], None] | None = None
    defaultFocusValue: T | None = None
    defaultInputModeValue: T | None = None
    layout: str = "compact"
    inlineDescriptions: bool = False
    onUpFromFirstItem: Callable[[], None] | None = None
    onDownFromLastItem: Callable[[], None] | None = None
    onInputModeToggle: Callable[[T], None] | None = None
    normalizedOptions: list[OptionWithDescription[T]] = field(init=False)
    focusedIndex: int = field(init=False, default=0)
    selectedValue: T | None = field(init=False, default=None)
    inputValues: dict[T, str] = field(init=False, default_factory=dict)
    inputModeValue: T | None = field(init=False, default=None)
    inputCursorOffset: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self.normalizedOptions = _coerce_options(self.options)
        initial_index = (
            _find_index_by_value(self.normalizedOptions, self.defaultFocusValue)
            if self.defaultFocusValue is not None
            else _find_index_by_value(self.normalizedOptions, self.defaultValue)
        )
        if initial_index is None:
            initial_index = 0
        self.focusedIndex = _next_enabled(self.normalizedOptions, initial_index, 1) if self.normalizedOptions else 0
        self.selectedValue = self.defaultValue
        self.inputValues = {
            option.value: (option.initialValue or "")
            for option in self.normalizedOptions
            if option.type == "input"
        }
        self.inputModeValue = self.defaultInputModeValue
        if self.inputModeValue is not None:
            self.inputCursorOffset = len(self.inputValues.get(self.inputModeValue, ""))
        self._emit_focus()

    @property
    def focusedOption(self) -> OptionWithDescription[T] | None:
        if not self.normalizedOptions:
            return None
        return self.normalizedOptions[self.focusedIndex]

    def _emit_focus(self) -> None:
        option = self.focusedOption
        if option is None or self.onFocus is None:
            return
        self.onFocus(option.value)

    def _move(self, step: int) -> None:
        if self.inputModeValue is not None:
            return
        if not self.normalizedOptions:
            return
        last_index = len(self.normalizedOptions) - 1
        if step < 0 and self.focusedIndex == 0 and self.onUpFromFirstItem is not None:
            self.onUpFromFirstItem()
            return
        if step > 0 and self.focusedIndex == last_index and self.onDownFromLastItem is not None:
            self.onDownFromLastItem()
            return
        next_index = (self.focusedIndex + step) % len(self.normalizedOptions)
        self.focusedIndex = _next_enabled(self.normalizedOptions, next_index, step or 1)
        self._emit_focus()

    def handleKeyDown(self, event: Any) -> None:
        if self.isDisabled:
            return
        key = str(getattr(event, "key", "")).lower()
        if self.inputModeValue is not None:
            option = self.focusedOption
            if option is None:
                return

            def _set_input_value(next_value: str) -> None:
                self.inputValues[option.value] = next_value

            def _set_cursor_offset(next_offset: int) -> None:
                self.inputCursorOffset = next_offset

            def _submit_input(value: str) -> None:
                trimmed = value.strip()
                self.inputValues[option.value] = value
                if trimmed or option.allowEmptySubmitToCancel:
                    if option.onChange is not None:
                        option.onChange(value)
                    self.inputModeValue = None
                    self.inputCursorOffset = len(value)
                    self.selectedValue = option.value
                    if self.onChange is not None:
                        self.onChange(option.value)
                else:
                    self.inputModeValue = None
                    self.inputCursorOffset = len(value)
                    if self.onCancel is not None:
                        self.onCancel()

            def _exit_input() -> None:
                self.inputModeValue = None
                self.inputCursorOffset = len(self.inputValues.get(option.value, ""))
                if self.onCancel is not None:
                    self.onCancel()

            text_input = TextInput(
                value=self.inputValues.get(option.value, ""),
                onChange=_set_input_value,
                columns=120,
                cursorOffset=self.inputCursorOffset,
                onChangeCursorOffset=_set_cursor_offset,
                placeholder=option.placeholder,
                focus=True,
                showCursor=True,
                onSubmit=_submit_input,
                onExit=_exit_input,
            )
            text_input.handleKeyDown(event)
            return
        if key == "up":
            self._move(-1)
            return
        if key == "down":
            self._move(1)
            return
        if key == "escape":
            if self.onCancel is not None:
                self.onCancel()
            return
        if key == "tab":
            option = self.focusedOption
            if option is None or option.disabled:
                return
            if self.onInputModeToggle is not None:
                self.onInputModeToggle(option.value)
                if option.type == "input":
                    if self.inputModeValue == option.value:
                        self.inputModeValue = None
                    else:
                        self.inputModeValue = option.value
                        self.inputCursorOffset = len(self.inputValues.get(option.value, ""))
                return
        if key == "return":
            if self.disableSelection:
                return
            option = self.focusedOption
            if option is None or option.disabled:
                return
            if option.type == "input":
                self.inputModeValue = option.value
                self.inputCursorOffset = len(self.inputValues.get(option.value, ""))
                return
            self.selectedValue = option.value
            if self.onChange is not None:
                self.onChange(option.value)

    def _window(self) -> tuple[int, int]:
        total = len(self.normalizedOptions)
        visible = max(1, min(self.visibleOptionCount, total))
        start = max(0, min(self.focusedIndex - visible // 2, max(0, total - visible)))
        return start, min(total, start + visible)

    def render_lines(self) -> list[str]:
        if not self.normalizedOptions:
            return ["No options"]
        start, end = self._window()
        lines: list[str] = []
        for index in range(start, end):
            option = self.normalizedOptions[index]
            marker = "❯" if index == self.focusedIndex else " "
            prefix = "" if self.hideIndexes else f"{index + 1}. "
            selected = " ✓" if self.selectedValue == option.value else ""
            disabled = " (disabled)" if option.disabled else ""
            label = str(option.label)
            if option.type == "input":
                current_value = self.inputValues.get(option.value, "")
                separator = option.labelValueSeparator or ", "
                show_label = self.inlineDescriptions or option.showLabelWithValue
                if self.inputModeValue == option.value:
                    input_preview = TextInput(
                        value=current_value,
                        onChange=lambda _value: None,
                        columns=120,
                        cursorOffset=self.inputCursorOffset,
                        onChangeCursorOffset=lambda _offset: None,
                        placeholder=option.placeholder,
                        focus=True,
                        showCursor=True,
                    ).render_lines()[0]
                    label = f"{label}{separator}{input_preview}" if show_label else input_preview
                elif current_value:
                    label = f"{label}{separator}{current_value}" if show_label else current_value
            if self.inlineDescriptions and option.description:
                label = f"{label} - {option.description}"
            lines.append(f"{marker} {prefix}{label}{selected}{disabled}")
            if option.description and not self.inlineDescriptions:
                lines.append(f"  {option.description}")
            if self.layout == "expanded" and index < end - 1:
                lines.append("")
        return lines


__all__ = ["OptionWithDescription", "Select"]