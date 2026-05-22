"""PowerShell permission request — compact port of src/components/permissions/PowerShellPermissionRequest.tsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ...services.analytics.index import logEvent
from ...tools.PowerShellTool.destructiveCommandWarning import getDestructiveCommandWarning
from ...tools.PowerShellTool.toolName import POWERSHELL_TOOL_NAME
from ...tools.PowerShellTool.UI import renderToolUseMessage
from ..CustomSelect.select import Select
from .PermissionDecisionDebugInfo import PermissionDecisionDebugInfo
from .PermissionDialog import PermissionDialog
from .PermissionRuleExplanation import PermissionRuleExplanation
from .powershellToolUseOptions import powershellToolUseOptions
from .useShellPermissionFeedback import ShellPermissionFeedbackState, useShellPermissionFeedback
from .utils import logUnaryPermissionEvent


def _tool_value(tool_use_confirm: Any, name: str, default: Any = None) -> Any:
    if hasattr(tool_use_confirm, name):
        return getattr(tool_use_confirm, name)
    if isinstance(tool_use_confirm, dict):
        return tool_use_confirm.get(name, default)
    return default


def _get_permission_result(tool_use_confirm: Any) -> dict[str, Any]:
    permission_result = _tool_value(tool_use_confirm, "permissionResult", {}) or {}
    return permission_result if isinstance(permission_result, dict) else {}


def _input_data(tool_use_confirm: Any) -> dict[str, Any]:
    input_data = _tool_value(tool_use_confirm, "input", {}) or {}
    return input_data if isinstance(input_data, dict) else {}


def _tool_is_mcp(tool_use_confirm: Any) -> bool:
    tool = _tool_value(tool_use_confirm, "tool", {}) or {}
    if isinstance(tool, dict):
        return bool(tool.get("isMcp", False))
    return bool(getattr(tool, "isMcp", False))


def _has_debug(tool_use_context: Any) -> bool:
    options = getattr(tool_use_context, "options", None)
    if options is None and isinstance(tool_use_context, dict):
        options = tool_use_context.get("options")
    if isinstance(options, dict):
        return bool(options.get("debug", False))
    return bool(getattr(options, "debug", False)) if options is not None else False


@dataclass
class PowerShellPermissionRequest:
    toolUseConfirm: Any
    toolUseContext: Any
    onDone: Callable[[], None]
    onReject: Callable[[], None]
    workerBadge: Any = None
    _feedback: ShellPermissionFeedbackState = field(init=False)
    _select: Select[str] = field(init=False)
    _editable_prefix: str | None = field(init=False, default=None)
    _show_permission_debug: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        input_data = _input_data(self.toolUseConfirm)
        self.command = str(input_data.get("command") or "")
        self.description = str(input_data.get("description") or _tool_value(self.toolUseConfirm, "description", "") or "")
        self._editable_prefix = None if "\n" in self.command else (self.command or None)
        self._feedback = useShellPermissionFeedback(
            toolUseConfirm=self.toolUseConfirm,
            onDone=self.onDone,
            onReject=self.onReject,
            explainerVisible=False,
        )
        self._select = self._build_select()

    def _set_accept_feedback(self, value: str) -> None:
        self._feedback.setAcceptFeedback(value)

    def _set_reject_feedback(self, value: str) -> None:
        self._feedback.setRejectFeedback(value)

    def _set_editable_prefix(self, value: str) -> None:
        self._editable_prefix = value

    def _handle_input_mode_toggle(self, value: str) -> None:
        self._feedback.handleInputModeToggle(value)
        self._select = self._build_select(preserve_focus=True)

    def _handle_focus(self, value: str) -> None:
        before = (self._feedback.yesInputMode, self._feedback.noInputMode, self._feedback.focusedOption)
        self._feedback.handleFocus(value)
        after = (self._feedback.yesInputMode, self._feedback.noInputMode, self._feedback.focusedOption)
        if before != after:
            self._select = self._build_select(preserve_focus=True)

    def _build_select(self, preserve_focus: bool = False) -> Select[str]:
        default_focus_value = self._feedback.focusedOption if preserve_focus else None
        default_input_value = None
        if preserve_focus and (self._feedback.yesInputMode or self._feedback.noInputMode):
            default_input_value = self._feedback.focusedOption
        return Select(
            options=powershellToolUseOptions(
                suggestions=_get_permission_result(self.toolUseConfirm).get("suggestions") if _get_permission_result(self.toolUseConfirm).get("behavior") == "ask" else None,
                onRejectFeedbackChange=self._set_reject_feedback,
                onAcceptFeedbackChange=self._set_accept_feedback,
                yesInputMode=self._feedback.yesInputMode,
                noInputMode=self._feedback.noInputMode,
                editablePrefix=self._editable_prefix,
                onEditablePrefixChange=self._set_editable_prefix,
            ),
            inlineDescriptions=True,
            onChange=self._handle_select,
            onCancel=lambda: self._feedback.handleReject(),
            onFocus=self._handle_focus,
            onInputModeToggle=self._handle_input_mode_toggle,
            defaultFocusValue=default_focus_value,
            defaultInputModeValue=default_input_value,
        )

    def _handle_select(self, value: str) -> None:
        permission_result = _get_permission_result(self.toolUseConfirm)
        input_data = _input_data(self.toolUseConfirm)
        logEvent(
            "tengu_permission_request_option_selected",
            {
                "option_index": {
                    "yes": 1,
                    "yes-apply-suggestions": 2,
                    "yes-prefix-edited": 2,
                    "no": 3,
                }.get(value, 0),
                "explainer_visible": False,
            },
        )
        on_allow = _tool_value(self.toolUseConfirm, "onAllow")
        if value == "yes-prefix-edited":
            trimmed_prefix = (self._editable_prefix or "").strip()
            logUnaryPermissionEvent("tool_use_single", self.toolUseConfirm, "accept")
            if callable(on_allow):
                if trimmed_prefix:
                    on_allow(
                        input_data,
                        [{
                            "type": "addRules",
                            "rules": [{"toolName": POWERSHELL_TOOL_NAME, "ruleContent": trimmed_prefix}],
                            "behavior": "allow",
                            "destination": "localSettings",
                        }],
                    )
                else:
                    on_allow(input_data, [])
            self.onDone()
            return
        if value == "yes":
            trimmed_feedback = self._feedback.acceptFeedback.strip()
            logUnaryPermissionEvent("tool_use_single", self.toolUseConfirm, "accept")
            logEvent(
                "tengu_accept_submitted",
                {
                    "toolName": POWERSHELL_TOOL_NAME,
                    "isMcp": _tool_is_mcp(self.toolUseConfirm),
                    "has_instructions": bool(trimmed_feedback),
                    "instructions_length": len(trimmed_feedback),
                    "entered_feedback_mode": self._feedback.yesFeedbackModeEntered,
                },
            )
            if callable(on_allow):
                on_allow(input_data, [], trimmed_feedback or None)
            self.onDone()
            return
        if value == "yes-apply-suggestions":
            logUnaryPermissionEvent("tool_use_single", self.toolUseConfirm, "accept")
            if callable(on_allow):
                on_allow(input_data, permission_result.get("suggestions") or [])
            self.onDone()
            return
        if value == "no":
            trimmed_feedback = self._feedback.rejectFeedback.strip()
            logEvent(
                "tengu_reject_submitted",
                {
                    "toolName": POWERSHELL_TOOL_NAME,
                    "isMcp": _tool_is_mcp(self.toolUseConfirm),
                    "has_instructions": bool(trimmed_feedback),
                    "instructions_length": len(trimmed_feedback),
                    "entered_feedback_mode": self._feedback.noFeedbackModeEntered,
                },
            )
            self._feedback.handleReject(trimmed_feedback or None)

    def handleKeyDown(self, event: Any) -> None:
        self._select.handleKeyDown(event)

    def render_lines(self) -> list[str]:
        permission_result = _get_permission_result(self.toolUseConfirm)
        lines = [renderToolUseMessage({"command": self.command, "description": self.description})]
        if self.description:
            lines.append(self.description)
        explanation_lines = PermissionRuleExplanation(permissionResult=permission_result, toolType="command").render_lines()
        if explanation_lines:
            lines.append("")
            lines.extend(explanation_lines)
        destructive_warning = getDestructiveCommandWarning(self.command)
        if destructive_warning:
            lines.append(destructive_warning)
        if self._show_permission_debug and _has_debug(self.toolUseContext):
            lines.append("")
            lines.extend(PermissionDecisionDebugInfo(permissionResult=permission_result, toolName="PowerShell").render_lines())
        else:
            lines.append("Do you want to proceed?")
            lines.extend(self._select.render_lines())
            hint = "Esc to cancel"
            if ((self._feedback.focusedOption == "yes" and not self._feedback.yesInputMode) or (self._feedback.focusedOption == "no" and not self._feedback.noInputMode)):
                hint = f"{hint} · Tab to amend"
            lines.append(hint)
        return PermissionDialog(title="PowerShell command", children=lines, workerBadge=self.workerBadge).render_lines()


__all__ = ["PowerShellPermissionRequest"]