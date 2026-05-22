"""Permission rule input — minimal port of src/components/permissions/rules/PermissionRuleInput.tsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ....hooks.useExitOnCtrlCDWithKeybindings import useExitOnCtrlCDWithKeybindings
from ....keybindings.useKeybinding import useKeybinding
from ....tools.BashTool.toolName import BASH_TOOL_NAME
from ....tools.WebFetchTool.WebFetchTool import TOOL_NAME as WEB_FETCH_TOOL_NAME
from ....utils.permissions.permissionRuleParser import (
    permissionRuleValueFromString,
    permissionRuleValueToString,
)
from ...TextInput import TextInput


ELLIPSIS = "..."


@dataclass
class PermissionRuleInput:
    onCancel: Callable[[], None]
    onSubmit: Callable[[dict[str, Any], str], None]
    ruleBehavior: str
    columns: int = 80
    inputValue: str = field(default="", init=False)
    cursorOffset: int = field(default=0, init=False)
    exitState: dict[str, Any] = field(init=False)
    input: TextInput = field(init=False)

    def __post_init__(self) -> None:
        self.exitState = useExitOnCtrlCDWithKeybindings()
        useKeybinding("confirm:no", self.onCancel, {"context": "Settings"})
        self.input = TextInput(
            showCursor=True,
            value=self.inputValue,
            onChange=self._handle_change,
            onSubmit=self._handle_submit,
            onExit=self.onCancel,
            placeholder=f"Enter permission rule{ELLIPSIS}",
            columns=max(self.columns - 6, 10),
            cursorOffset=self.cursorOffset,
            onChangeCursorOffset=self._handle_cursor_change,
            multiline=False,
        )

    def _handle_change(self, value: str) -> None:
        self.inputValue = value
        self.input.value = value

    def _handle_cursor_change(self, offset: int) -> None:
        self.cursorOffset = offset
        self.input.cursorOffset = offset

    def _handle_submit(self, value: str) -> None:
        trimmed = value.strip()
        if not trimmed:
            return
        rule_value = permissionRuleValueFromString(trimmed)
        self.onSubmit(rule_value, self.ruleBehavior)

    def handleKeyDown(self, event: Any) -> None:
        self.input.handleKeyDown(event)

    def render_lines(self) -> list[str]:
        self.input.columns = max(self.columns - 6, 10)
        input_line = self.input.render_lines()[0] if self.input.render_lines() else ""
        example_web = permissionRuleValueToString({"toolName": WEB_FETCH_TOOL_NAME})
        example_bash = permissionRuleValueToString({"toolName": BASH_TOOL_NAME, "ruleContent": "ls:*"})
        footer = (
            f"Press {self.exitState.get('keyName')} again to exit"
            if self.exitState.get("pending")
            else "Enter to submit · Esc to cancel"
        )
        border = "(" + ("-" * max(self.columns - 2, 18)) + ")"
        return [
            border,
            f" Add {self.ruleBehavior} permission rule",
            " Permission rules are a tool name, optionally followed by a specifier in parentheses.",
            f" e.g., {example_web} or {example_bash}",
            f" {input_line}",
            border,
            f"   {footer}",
        ]


__all__ = ["PermissionRuleInput"]