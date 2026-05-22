"""Output style picker — minimal port of src/components/OutputStylePicker.tsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..constants.outputStyles import OUTPUT_STYLE_CONFIG, getAllOutputStyles
from ..utils.cwd import get_cwd
from .CustomSelect import OptionWithDescription, Select
from .design_system import Dialog


DEFAULT_OUTPUT_STYLE_LABEL = "Default"
DEFAULT_OUTPUT_STYLE_DESCRIPTION = "vivian completes coding tasks efficiently and provides concise responses"


def mapConfigsToOptions(styles: dict[str, dict | None]) -> list[OptionWithDescription[str]]:
    return [
        OptionWithDescription(
            label=(config or {}).get("name", DEFAULT_OUTPUT_STYLE_LABEL),
            value=style,
            description=(config or {}).get("description", DEFAULT_OUTPUT_STYLE_DESCRIPTION),
        )
        for style, config in styles.items()
    ]


@dataclass
class OutputStylePicker:
    initialStyle: str
    onComplete: Callable[[str], None]
    onCancel: Callable[[], None]
    isStandaloneCommand: bool = False
    styleOptions: list[OptionWithDescription[str]] = field(init=False)
    isLoading: bool = field(init=False, default=True)
    select: Select[str] | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        try:
            all_styles = getAllOutputStyles(get_cwd())
        except Exception:
            all_styles = OUTPUT_STYLE_CONFIG
        self.styleOptions = mapConfigsToOptions(all_styles)
        self.isLoading = False
        self.select = Select(
            options=self.styleOptions,
            onChange=self._handle_style_select,
            onCancel=self.onCancel,
            visibleOptionCount=10,
            defaultValue=self.initialStyle,
            defaultFocusValue=self.initialStyle,
        )

    def _handle_style_select(self, style: str) -> None:
        self.onComplete(style)

    def handleKeyDown(self, event: object) -> None:
        if self.select is not None:
            self.select.handleKeyDown(event)

    def render_lines(self) -> list[str]:
        lines = ["This changes how vivian Code communicates with you"]
        if self.isLoading or self.select is None:
            lines.append("Loading output styles...")
        else:
            lines.extend(self.select.render_lines())
        dialog = Dialog(
            title="Preferred output style",
            onCancel=self.onCancel,
            hideInputGuide=not self.isStandaloneCommand,
            hideBorder=not self.isStandaloneCommand,
            children=lines,
        )
        return dialog.render_lines()


__all__ = ["DEFAULT_OUTPUT_STYLE_DESCRIPTION", "DEFAULT_OUTPUT_STYLE_LABEL", "OutputStylePicker", "mapConfigsToOptions"]