"""Thinking toggle — focused port of src/components/ThinkingToggle.tsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..hooks.useExitOnCtrlCDWithKeybindings import useExitOnCtrlCDWithKeybindings
from ..keybindings.useKeybinding import useKeybinding
from .ConfigurableShortcutHint import ConfigurableShortcutHint
from .CustomSelect import OptionWithDescription, Select
from .design_system import Byline, KeyboardShortcutHint, Pane


@dataclass
class ThinkingToggle:
    currentValue: bool
    onSelect: Callable[[bool], None]
    onCancel: Callable[[], None] | None = None
    isMidConversation: bool = False
    confirmationPending: bool | None = field(init=False, default=None)
    select: Select[str] = field(init=False)

    def __post_init__(self) -> None:
        self.select = Select(
            defaultValue="true" if self.currentValue else "false",
            defaultFocusValue="true" if self.currentValue else "false",
            options=self._options(),
            onChange=self._handle_select_change,
            onCancel=self.onCancel or (lambda: None),
            visibleOptionCount=2,
        )
        useKeybinding("confirm:no", self._handle_cancel_key, {"context": "Confirmation"})
        useKeybinding(
            "confirm:yes",
            self._confirm_pending,
            {"context": "Confirmation", "isActive": self.confirmationPending is not None},
        )

    def _options(self) -> list[OptionWithDescription[str]]:
        return [
            OptionWithDescription(
                value="true",
                label="Enabled",
                description="vivian will think before responding",
            ),
            OptionWithDescription(
                value="false",
                label="Disabled",
                description="vivian will respond without extended thinking",
            ),
        ]

    def _handle_cancel_key(self) -> None:
        if self.confirmationPending is not None:
            self.confirmationPending = None
            return
        if self.onCancel is not None:
            self.onCancel()

    def _confirm_pending(self) -> None:
        if self.confirmationPending is not None:
            self.onSelect(self.confirmationPending)

    def _handle_select_change(self, value: str) -> None:
        selected = value == "true"
        if self.isMidConversation and selected != self.currentValue:
            self.confirmationPending = selected
            return
        self.onSelect(selected)

    def handleKeyDown(self, event: object) -> None:
        if self.confirmationPending is None:
            self.select.handleKeyDown(event)
            return

        key = str(getattr(event, "key", "")).lower()
        if key == "return":
            self._confirm_pending()
        elif key == "escape":
            self._handle_cancel_key()

    def render_lines(self) -> list[str]:
        exit_state = useExitOnCtrlCDWithKeybindings()
        body = [
            "Toggle thinking mode",
            "Enable or disable thinking for this session.",
            "",
        ]
        if self.confirmationPending is not None:
            body.extend(
                [
                    "Changing thinking mode mid-conversation will increase latency and may reduce quality.",
                    "For best results, set this at the start of a session.",
                    "Do you want to proceed?",
                ]
            )
        else:
            body.extend(self.select.render_lines())

        if exit_state.get("pending"):
            footer = f"Press {exit_state.get('keyName')} again to exit"
        elif self.confirmationPending is not None:
            footer = str(
                Byline(
                    [
                        KeyboardShortcutHint(shortcut="Enter", action="confirm"),
                        ConfigurableShortcutHint(
                            action="confirm:no",
                            context="Confirmation",
                            fallback="Esc",
                            description="cancel",
                        ),
                    ]
                )
            )
        else:
            footer = str(
                Byline(
                    [
                        KeyboardShortcutHint(shortcut="Enter", action="confirm"),
                        ConfigurableShortcutHint(
                            action="confirm:no",
                            context="Confirmation",
                            fallback="Esc",
                            description="exit",
                        ),
                    ]
                )
            )

        return Pane(children=body + [footer], color="permission").render_lines()


__all__ = ["ThinkingToggle"]