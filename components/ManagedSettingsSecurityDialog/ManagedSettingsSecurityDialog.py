"""ManagedSettingsSecurityDialog.

Mirrors src/components/ManagedSettingsSecurityDialog/ManagedSettingsSecurityDialog.tsx.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

from .utils import extractDangerousSettings, formatDangerousSettingsList


@dataclass(slots=True)
class ManagedSettingsSecurityDialog:
    settings: Optional[Mapping[str, Any]]
    onAccept: Optional[Callable[[], None]] = None
    onReject: Optional[Callable[[], None]] = None
    settingsList: list[str] = None  # type: ignore[assignment]
    title: str = ""

    def __post_init__(self) -> None:
        dangerous = extractDangerousSettings(self.settings)
        self.settingsList = formatDangerousSettingsList(dangerous)
        self.title = "Managed settings require approval"

    def render_lines(self) -> list[str]:
        lines = [
            self.title,
            "",
            "Your organization has configured managed settings that could allow execution of arbitrary code or interception of your prompts and responses.",
            "",
            "Settings requiring approval:",
        ]
        lines.extend(f"  - {item}" for item in self.settingsList)
        lines.extend(
            [
                "",
                "Only accept if you trust your organization's IT administration and expect these settings to be configured.",
                "",
                "[1] Yes, I trust these settings",
                "[2] No, exit vivian Code",
            ]
        )
        return lines

    def onChange(self, value: str) -> str:
        if value == "exit":
            if self.onReject is not None:
                self.onReject()
            return "rejected"
        if self.onAccept is not None:
            self.onAccept()
        return "approved"

    def show(self, input_fn: Callable[[str], str] = input, output_fn: Callable[[str], None] = print) -> str:
        for line in self.render_lines():
            output_fn(line)

        while True:
            choice = input_fn("Select 1 to accept or 2 to exit: ").strip().lower()
            if choice in {"1", "accept", "a", "yes", "y", ""}:
                return self.onChange("accept")
            if choice in {"2", "exit", "reject", "r", "no", "n", "esc"}:
                return self.onChange("exit")
            output_fn("Invalid selection. Enter 1 to accept or 2 to exit.")


def show_managed_settings_security_dialog(
    settings: Optional[Mapping[str, Any]],
    parent: Any = None,
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> str:
    del parent
    dialog = ManagedSettingsSecurityDialog(settings=settings)
    return dialog.show(input_fn=input_fn, output_fn=output_fn)