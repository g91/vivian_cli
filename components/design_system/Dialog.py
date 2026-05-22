"""Dialog component — functional port of src/components/design-system/Dialog.tsx."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ...hooks.useExitOnCtrlCDWithKeybindings import useExitOnCtrlCDWithKeybindings
from ...keybindings.useKeybinding import useKeybinding
from ..ConfigurableShortcutHint import ConfigurableShortcutHint
from .Byline import Byline
from .KeyboardShortcutHint import KeyboardShortcutHint
from .Pane import Pane
from .ThemedText import ThemedText


def _coerce_lines(children: Any) -> list[str]:
    if children is None:
        return []
    if isinstance(children, str):
        return [children]
    if isinstance(children, list):
        return [str(line) for line in children]
    render_lines = getattr(children, "render_lines", None)
    if callable(render_lines):
        return [str(line) for line in render_lines()]
    render = getattr(children, "render", None)
    if callable(render):
        return [str(render())]
    return [str(children)]


@dataclass(slots=True)
class Dialog:
    title: Any
    children: Any
    onCancel: Callable[[], None]
    subtitle: Any = None
    color: str = "permission"
    hideInputGuide: bool = False
    hideBorder: bool = False
    inputGuide: Callable[[dict[str, Any]], Any] | None = None
    isCancelActive: bool = True

    def render_lines(self) -> list[str]:
        exit_state = useExitOnCtrlCDWithKeybindings()
        useKeybinding(
            "confirm:no",
            self.onCancel,
            {"context": "Confirmation", "isActive": self.isCancelActive},
        )

        if exit_state.get("pending"):
            default_input_guide = f"Press {exit_state.get('keyName')} again to exit"
        else:
            default_input_guide = Byline(
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

        lines = [str(ThemedText(children=self.title, color=self.color, bold=True))]
        if self.subtitle not in (None, False, ""):
            lines.append(str(ThemedText(children=self.subtitle, dimColor=True)))
        lines.extend(_coerce_lines(self.children))

        if not self.hideInputGuide:
            guide = self.inputGuide(exit_state) if self.inputGuide is not None else default_input_guide
            if guide not in (None, False, ""):
                lines.append("")
                lines.extend(_coerce_lines(ThemedText(children=guide, dimColor=True, italic=True)))

        if self.hideBorder:
            return lines
        return Pane(children=lines, color=self.color).render_lines()


__all__ = ["Dialog"]