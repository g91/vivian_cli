"""Enter plan mode permission request — focused port of src/components/permissions/EnterPlanModePermissionRequest/EnterPlanModePermissionRequest.tsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from ...bootstrap.state import handlePlanModeTransition
from ...services.analytics.index import logEvent
from ...state.AppState import useAppStateMaybeOutsideOfProvider
from ...utils.planModeV2 import isPlanModeInterviewPhaseEnabled
from ..CustomSelect import OptionWithDescription, Select
from .PermissionDialog import PermissionDialog


EnterPlanModeSelection = Literal["yes", "no"]


@dataclass
class EnterPlanModePermissionRequest:
    toolUseConfirm: Any
    onDone: Callable[[], None]
    onReject: Callable[[], None]
    workerBadge: Any = None
    select: Select[EnterPlanModeSelection] = field(init=False)

    def __post_init__(self) -> None:
        self.select = Select(
            options=[
                OptionWithDescription(label="Yes, enter plan mode", value="yes"),
                OptionWithDescription(label="No, start implementing now", value="no"),
            ],
            onChange=self._handle_response,
            onCancel=self._handle_cancel,
        )

    def _tool_value(self, name: str, default: Any = None) -> Any:
        if hasattr(self.toolUseConfirm, name):
            return getattr(self.toolUseConfirm, name)
        if isinstance(self.toolUseConfirm, dict):
            return self.toolUseConfirm.get(name, default)
        return default

    def _current_mode(self) -> str:
        mode = useAppStateMaybeOutsideOfProvider(lambda state: state.toolPermissionContext.mode)
        return str(mode or "default")

    def _handle_response(self, value: EnterPlanModeSelection) -> None:
        if value == "yes":
            logEvent(
                "tengu_plan_enter",
                {
                    "interviewPhaseEnabled": bool(isPlanModeInterviewPhaseEnabled()),
                    "entryMethod": "tool",
                },
            )
            current_mode = self._current_mode()
            handlePlanModeTransition(current_mode, "plan")
            self.onDone()
            on_allow = self._tool_value("onAllow")
            if callable(on_allow):
                on_allow({}, [{"type": "setMode", "mode": "plan", "destination": "session"}])
            return
        self.onDone()
        self.onReject()
        on_reject = self._tool_value("onReject")
        if callable(on_reject):
            on_reject()

    def _handle_cancel(self) -> None:
        self._handle_response("no")

    def handleKeyDown(self, event: object) -> None:
        self.select.handleKeyDown(event)

    def render_lines(self) -> list[str]:
        children = [
            "vivian wants to enter plan mode to explore and design an implementation approach.",
            "",
            "In plan mode, vivian will:",
            " - Explore the codebase thoroughly",
            " - Identify existing patterns",
            " - Design an implementation strategy",
            " - Present a plan for your approval",
            "",
            "No code changes will be made until you approve the plan.",
            "",
            *self.select.render_lines(),
        ]
        return PermissionDialog(
            color="planMode",
            title="Enter plan mode?",
            workerBadge=self.workerBadge,
            children=children,
        ).render_lines()


__all__ = ["EnterPlanModePermissionRequest", "EnterPlanModeSelection"]