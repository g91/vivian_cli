"""Theme picker — focused port of src/components/ThemePicker.tsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..keybindings.KeybindingContext import useRegisterKeybindingContext
from ..keybindings.useShortcutDisplay import useShortcutDisplay
from ..utils.gracefulShutdown import graceful_shutdown
from ..utils.theme import ThemeSetting
from .CustomSelect import OptionWithDescription, Select
from .design_system import usePreviewTheme, useTheme, useThemeSetting


def _theme_options() -> list[OptionWithDescription[ThemeSetting]]:
    return [
        OptionWithDescription(label="Auto (match terminal)", value="auto"),
        OptionWithDescription(label="Dark mode", value="dark"),
        OptionWithDescription(label="Light mode", value="light"),
        OptionWithDescription(label="Dark mode (colorblind-friendly)", value="dark-daltonized"),
        OptionWithDescription(label="Light mode (colorblind-friendly)", value="light-daltonized"),
        OptionWithDescription(label="Dark mode (ANSI colors only)", value="dark-ansi"),
        OptionWithDescription(label="Light mode (ANSI colors only)", value="light-ansi"),
    ]


@dataclass
class ThemePicker:
    onThemeSelect: Callable[[ThemeSetting], None]
    showIntroText: bool = False
    helpText: str = ""
    showHelpTextBelow: bool = False
    hideEscToCancel: bool = False
    skipExitHandling: bool = False
    onCancel: Callable[[], None] | None = None
    select: Select[ThemeSetting] = field(init=False)
    syntaxToggleShortcut: str = field(init=False)

    def __post_init__(self) -> None:
        _, _set_theme = useTheme()
        theme_setting = useThemeSetting()
        preview = usePreviewTheme()
        useRegisterKeybindingContext("ThemePicker")
        self.syntaxToggleShortcut = useShortcutDisplay(
            "theme:toggleSyntaxHighlighting",
            "ThemePicker",
            "ctrl+t",
        )

        def handle_focus(setting: ThemeSetting) -> None:
            preview.setPreviewTheme(setting)

        def handle_change(setting: ThemeSetting) -> None:
            preview.savePreview()
            _set_theme(setting)
            self.onThemeSelect(setting)

        def handle_cancel() -> None:
            preview.cancelPreview()
            if self.skipExitHandling:
                if self.onCancel is not None:
                    self.onCancel()
                return
            graceful_shutdown(0)

        self.select = Select(
            options=_theme_options(),
            onFocus=handle_focus,
            onChange=handle_change,
            onCancel=handle_cancel,
            visibleOptionCount=len(_theme_options()),
            defaultValue=theme_setting,
            defaultFocusValue=theme_setting,
        )

    def handleKeyDown(self, event: object) -> None:
        self.select.handleKeyDown(event)

    def render_lines(self) -> list[str]:
        current_theme = useTheme()[0]
        lines: list[str] = []
        if self.showIntroText:
            lines.append("Let's get started.")
        else:
            lines.append("Theme")
        lines.append("Choose the text style that looks best with your terminal")
        if self.helpText and not self.showHelpTextBelow:
            lines.append(self.helpText)
        lines.extend(self.select.render_lines())
        lines.append("")
        lines.append("Preview")
        lines.append(" function greet() {")
        lines.append("-  console.log(\"Hello, World!\");")
        lines.append("+  console.log(\"Hello, vivian!\");")
        lines.append(" }")
        lines.append(f"Current preview theme: {current_theme}")
        lines.append(f"Syntax highlighting available shortcut: {self.syntaxToggleShortcut}")
        if self.showHelpTextBelow and self.helpText:
            lines.append(self.helpText)
        if not self.hideEscToCancel:
            lines.append("Enter to select · Esc to cancel")
        return lines


__all__ = ["ThemePicker"]