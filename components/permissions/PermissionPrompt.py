"""Permission prompt — compact shared prompt with optional feedback input."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Generic, TypeVar

from ...services.analytics.index import logEvent
from ..CustomSelect import OptionWithDescription, Select


T = TypeVar("T", bound=str)


DEFAULT_PLACEHOLDERS = {
    "accept": "tell vivian what to do next",
    "reject": "tell vivian what to do differently",
}


@dataclass(slots=True)
class ToolAnalyticsContext:
    toolName: str
    isMcp: bool = False


@dataclass(slots=True)
class PermissionPromptOption(Generic[T]):
    value: T
    label: Any
    feedbackConfig: dict[str, Any] | None = None
    keybinding: str | None = None


@dataclass
class PermissionPrompt(Generic[T]):
    options: list[PermissionPromptOption[T]]
    onSelect: Callable[[T, str | None], None]
    onCancel: Callable[[], None] | None = None
    question: Any = "Do you want to proceed?"
    toolAnalyticsContext: ToolAnalyticsContext | None = None
    acceptFeedback: str = field(init=False, default="")
    rejectFeedback: str = field(init=False, default="")
    acceptInputMode: bool = field(init=False, default=False)
    rejectInputMode: bool = field(init=False, default=False)
    acceptFeedbackModeEntered: bool = field(init=False, default=False)
    rejectFeedbackModeEntered: bool = field(init=False, default=False)
    focusedValue: T | None = field(init=False, default=None)
    select: Select[T] = field(init=False)

    def __post_init__(self) -> None:
        self.select = self._build_select()

    def _analytics_props(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        props = {
            "toolName": self.toolAnalyticsContext.toolName if self.toolAnalyticsContext else None,
            "isMcp": self.toolAnalyticsContext.isMcp if self.toolAnalyticsContext else False,
        }
        if extra:
            props.update(extra)
        return props

    def _focused_option(self) -> PermissionPromptOption[T] | None:
        if self.focusedValue is None:
            return None
        return next((option for option in self.options if option.value == self.focusedValue), None)

    def _show_tab_hint(self) -> bool:
        option = self._focused_option()
        feedback_type = None if option is None or option.feedbackConfig is None else option.feedbackConfig.get("type")
        return (feedback_type == "accept" and not self.acceptInputMode) or (feedback_type == "reject" and not self.rejectInputMode)

    def _toggle_input_mode(self, value: T) -> None:
        option = next((item for item in self.options if item.value == value), None)
        if option is None or option.feedbackConfig is None:
            return
        feedback_type = option.feedbackConfig.get("type")
        if feedback_type == "accept":
            self.acceptInputMode = not self.acceptInputMode
            if self.acceptInputMode:
                self.acceptFeedbackModeEntered = True
                logEvent("tengu_accept_feedback_mode_entered", self._analytics_props())
            else:
                logEvent("tengu_accept_feedback_mode_collapsed", self._analytics_props())
        elif feedback_type == "reject":
            self.rejectInputMode = not self.rejectInputMode
            if self.rejectInputMode:
                self.rejectFeedbackModeEntered = True
                logEvent("tengu_reject_feedback_mode_entered", self._analytics_props())
            else:
                logEvent("tengu_reject_feedback_mode_collapsed", self._analytics_props())
        self.select = self._build_select(preserve_focus=True)

    def _handle_focus(self, value: T) -> None:
        if self.focusedValue == value:
            return
        next_option = next((item for item in self.options if item.value == value), None)
        if next_option is None:
            return
        next_feedback = None if next_option.feedbackConfig is None else next_option.feedbackConfig.get("type")
        if next_feedback != "accept" and self.acceptInputMode and not self.acceptFeedback.strip():
            self.acceptInputMode = False
        if next_feedback != "reject" and self.rejectInputMode and not self.rejectFeedback.strip():
            self.rejectInputMode = False
        self.focusedValue = value

    def _feedback_for(self, option: PermissionPromptOption[T]) -> str | None:
        if option.feedbackConfig is None:
            return None
        feedback_type = option.feedbackConfig.get("type")
        raw = self.acceptFeedback if feedback_type == "accept" else self.rejectFeedback
        trimmed = raw.strip()
        analytics_props = self._analytics_props(
            {
                "has_instructions": bool(trimmed),
                "instructions_length": len(trimmed),
                "entered_feedback_mode": self.acceptFeedbackModeEntered if feedback_type == "accept" else self.rejectFeedbackModeEntered,
            }
        )
        if feedback_type == "accept":
            logEvent("tengu_accept_submitted", analytics_props)
        elif feedback_type == "reject":
            logEvent("tengu_reject_submitted", analytics_props)
        return trimmed or None

    def _handle_select(self, value: T) -> None:
        option = next((item for item in self.options if item.value == value), None)
        if option is None:
            return
        self.onSelect(value, self._feedback_for(option))

    def _handle_cancel(self) -> None:
        logEvent("tengu_permission_request_escape", {})
        if self.onCancel is not None:
            self.onCancel()

    def _build_select(self, preserve_focus: bool = False) -> Select[T]:
        select_options: list[OptionWithDescription[T]] = []
        default_input_mode_value: T | None = None
        for option in self.options:
            feedback = option.feedbackConfig or {}
            feedback_type = feedback.get("type")
            is_input_mode = (feedback_type == "accept" and self.acceptInputMode) or (
                feedback_type == "reject" and self.rejectInputMode
            )
            if is_input_mode:
                default_input_mode_value = option.value
                current_value = self.acceptFeedback if feedback_type == "accept" else self.rejectFeedback
                placeholder = feedback.get("placeholder") or DEFAULT_PLACEHOLDERS.get(feedback_type or "", "")

                def _make_on_change(kind: str | None) -> Callable[[str], None]:
                    def _on_change(next_value: str) -> None:
                        if kind == "accept":
                            self.acceptFeedback = next_value
                        else:
                            self.rejectFeedback = next_value
                    return _on_change

                select_options.append(
                    OptionWithDescription(
                        label=option.label,
                        value=option.value,
                        type="input",
                        onChange=_make_on_change(feedback_type),
                        placeholder=placeholder,
                        initialValue=current_value,
                        allowEmptySubmitToCancel=True,
                    )
                )
            else:
                select_options.append(OptionWithDescription(label=option.label, value=option.value))
        return Select(
            options=select_options,
            inlineDescriptions=True,
            onChange=self._handle_select,
            onCancel=self._handle_cancel,
            onFocus=self._handle_focus,
            onInputModeToggle=self._toggle_input_mode,
            defaultFocusValue=self.focusedValue if preserve_focus else None,
            defaultInputModeValue=default_input_mode_value,
        )

    def handleKeyDown(self, event: Any) -> None:
        self.select.handleKeyDown(event)

    def render_lines(self) -> list[str]:
        lines = [str(self.question)]
        lines.extend(self.select.render_lines())
        hint = "Esc to cancel"
        if self._show_tab_hint():
            hint = f"{hint} · Tab to amend"
        lines.append(hint)
        return lines


__all__ = ["PermissionPrompt", "PermissionPromptOption", "ToolAnalyticsContext"]