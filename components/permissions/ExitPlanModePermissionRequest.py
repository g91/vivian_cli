"""Exit plan mode permission request — compact port of src/components/permissions/ExitPlanModePermissionRequest/ExitPlanModePermissionRequest.tsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ...state.AppState import useAppStateMaybeOutsideOfProvider
from .PermissionDialog import PermissionDialog
from .PermissionPrompt import PermissionPrompt, PermissionPromptOption, ToolAnalyticsContext


def _tool_value(tool_use_confirm: Any, name: str, default: Any = None) -> Any:
    if hasattr(tool_use_confirm, name):
        return getattr(tool_use_confirm, name)
    if isinstance(tool_use_confirm, dict):
        return tool_use_confirm.get(name, default)
    return default


def _input_data(tool_use_confirm: Any) -> dict[str, Any]:
    input_data = _tool_value(tool_use_confirm, "input", {}) or {}
    return input_data if isinstance(input_data, dict) else {}


@dataclass
class ExitPlanModePermissionRequest:
    toolUseConfirm: Any
    onDone: Callable[[], None]
    onReject: Callable[[], None]
    workerBadge: Any = None
    _tool_permission_context: dict[str, Any] = field(init=False, default_factory=dict)
    _prompt: PermissionPrompt[str] = field(init=False)

    def __post_init__(self) -> None:
        context = useAppStateMaybeOutsideOfProvider(lambda state: state.get("toolPermissionContext"))
        self._tool_permission_context = context if isinstance(context, dict) else {}
        self._prompt = PermissionPrompt(
            options=self._options(),
            onSelect=self._handle_select,
            onCancel=self._handle_cancel,
            toolAnalyticsContext=ToolAnalyticsContext(toolName="ExitPlanMode", isMcp=False),
        )

    def _options(self) -> list[PermissionPromptOption[str]]:
        options = [PermissionPromptOption(value="yes", label="Yes, start implementation", feedbackConfig={"type": "accept"})]
        options.append(PermissionPromptOption(value="yes-accept-edits", label="Yes, allow edits during this session"))
        if self._tool_permission_context.get("isBypassPermissionsModeAvailable"):
            options.append(PermissionPromptOption(value="yes-bypass-permissions", label="Yes, bypass permissions during this session"))
        options.append(PermissionPromptOption(value="no", label="No, stay in plan mode", feedbackConfig={"type": "reject"}))
        return options

    def _handle_select(self, value: str, feedback: str | None = None) -> None:
        input_data = dict(_input_data(self.toolUseConfirm))
        on_allow = _tool_value(self.toolUseConfirm, "onAllow")
        on_reject = _tool_value(self.toolUseConfirm, "onReject")
        if value == "no":
            if callable(on_reject):
                on_reject(feedback)
            self.onReject()
            self.onDone()
            return
        mode = "default"
        if value == "yes-accept-edits":
            mode = "acceptEdits"
        elif value == "yes-bypass-permissions":
            mode = "bypassPermissions"
        input_data["approved"] = True
        input_data["feedback"] = feedback or ""
        if callable(on_allow):
            on_allow(input_data, [{"type": "setMode", "mode": mode, "destination": "session"}], feedback)
        self.onDone()

    def _handle_cancel(self) -> None:
        self._handle_select("no")

    def handleKeyDown(self, event: Any) -> None:
        self._prompt.handleKeyDown(event)

    def render_lines(self) -> list[str]:
        plan = str(_input_data(self.toolUseConfirm).get("plan") or "")
        preview_lines = plan.splitlines()[:20]
        if len(plan.splitlines()) > 20:
            preview_lines.append("...")
        children = [
            "vivian has written a plan and wants to exit plan mode.",
            "",
            "Plan preview:",
            *preview_lines,
            "",
            *self._prompt.render_lines(),
        ]
        return PermissionDialog(title="Exit plan mode?", color="planMode", workerBadge=self.workerBadge, children=children).render_lines()


__all__ = ["ExitPlanModePermissionRequest"]