"""Port of src/hooks/useSettingsChange.ts."""
from __future__ import annotations

from typing import Callable

from ..utils.settings.changeDetector import watchSettingsFiles
from ..utils.settings.settings import getMergedSettings


def useSettingsChange(onChange: Callable[[str, dict], None]):
    def handle_change(source: str, _path: str) -> None:
        new_settings = getMergedSettings()
        onChange(source, new_settings)

    return watchSettingsFiles(handle_change)
