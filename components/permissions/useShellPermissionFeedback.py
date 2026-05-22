"""Shared feedback state for shell permission dialogs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ...services.analytics.index import logEvent
from ...state.AppState import useSetAppState
from .utils import logUnaryPermissionEvent


def _tool_value(tool_use_confirm: Any, name: str, default: Any = None) -> Any:
    if hasattr(tool_use_confirm, name):
        return getattr(tool_use_confirm, name)
    if isinstance(tool_use_confirm, dict):
        return tool_use_confirm.get(name, default)
    return default


def _sanitize_tool_name_for_analytics(name: Any) -> str:
    return str(name or "unknown")


@dataclass
class ShellPermissionFeedbackState:
    toolUseConfirm: Any
    onDone: Callable[[], None]
    onReject: Callable[[], None]
    explainerVisible: bool
    rejectFeedback: str = ""
    acceptFeedback: str = ""
    yesInputMode: bool = False
    noInputMode: bool = False
    focusedOption: str = "yes"
    yesFeedbackModeEntered: bool = False
    noFeedbackModeEntered: bool = False

    def __post_init__(self) -> None:
        try:
            self._set_app_state = useSetAppState()
        except Exception:
            self._set_app_state = None

    def _analytics_props(self) -> dict[str, Any]:
        tool = _tool_value(self.toolUseConfirm, "tool", {}) or {}
        if isinstance(tool, dict):
            name = tool.get("name")
            is_mcp = bool(tool.get("isMcp", False))
        else:
            name = getattr(tool, "name", None)
            is_mcp = bool(getattr(tool, "isMcp", False))
        return {
            "toolName": _sanitize_tool_name_for_analytics(name),
            "isMcp": is_mcp,
        }

    def handleInputModeToggle(self, option: str) -> None:
        on_user_interaction = _tool_value(self.toolUseConfirm, "onUserInteraction")
        if callable(on_user_interaction):
            on_user_interaction()
        analytics_props = self._analytics_props()
        if option == "yes":
            if self.yesInputMode:
                self.yesInputMode = False
                logEvent("tengu_accept_feedback_mode_collapsed", analytics_props)
            else:
                self.yesInputMode = True
                self.yesFeedbackModeEntered = True
                logEvent("tengu_accept_feedback_mode_entered", analytics_props)
        elif option == "no":
            if self.noInputMode:
                self.noInputMode = False
                logEvent("tengu_reject_feedback_mode_collapsed", analytics_props)
            else:
                self.noInputMode = True
                self.noFeedbackModeEntered = True
                logEvent("tengu_reject_feedback_mode_entered", analytics_props)

    def handleReject(self, feedback: str | None = None) -> None:
        trimmed_feedback = (feedback or "").strip()
        has_feedback = bool(trimmed_feedback)
        if not has_feedback:
            logEvent("tengu_permission_request_escape", {"explainer_visible": self.explainerVisible})
            if self._set_app_state is not None:
                self._set_app_state(
                    lambda prev: {
                        **prev,
                        "attribution": {
                            **prev.get("attribution", {}),
                            "escapeCount": prev.get("attribution", {}).get("escapeCount", 0) + 1,
                        },
                    }
                )
        logUnaryPermissionEvent("tool_use_single", self.toolUseConfirm, "reject", has_feedback)
        on_reject = _tool_value(self.toolUseConfirm, "onReject")
        if callable(on_reject):
            on_reject(trimmed_feedback or None)
        self.onReject()
        self.onDone()

    def handleFocus(self, value: str) -> None:
        on_user_interaction = _tool_value(self.toolUseConfirm, "onUserInteraction")
        if value != self.focusedOption and callable(on_user_interaction):
            on_user_interaction()
        if value != "yes" and self.yesInputMode and not self.acceptFeedback.strip():
            self.yesInputMode = False
        if value != "no" and self.noInputMode and not self.rejectFeedback.strip():
            self.noInputMode = False
        self.focusedOption = value

    def setAcceptFeedback(self, value: str) -> None:
        self.acceptFeedback = value

    def setRejectFeedback(self, value: str) -> None:
        self.rejectFeedback = value


def useShellPermissionFeedback(
    *,
    toolUseConfirm: Any,
    onDone: Callable[[], None],
    onReject: Callable[[], None],
    explainerVisible: bool,
) -> ShellPermissionFeedbackState:
    return ShellPermissionFeedbackState(
        toolUseConfirm=toolUseConfirm,
        onDone=onDone,
        onReject=onReject,
        explainerVisible=explainerVisible,
    )


__all__ = ["ShellPermissionFeedbackState", "useShellPermissionFeedback"]