"""Port of src/utils/deepLink/terminalPreference.ts."""
from __future__ import annotations

import os
import sys

from ..config import get_global_config, save_global_config
from ..debug import logForDebugging


TERM_PROGRAM_TO_APP = {
    "iterm": "iTerm",
    "iterm.app": "iTerm",
    "ghostty": "Ghostty",
    "kitty": "kitty",
    "alacritty": "Alacritty",
    "wezterm": "WezTerm",
    "apple_terminal": "Terminal",
}


def updateDeepLinkTerminalPreference():
    if sys.platform != "darwin":
        return
    term_program = os.environ.get("TERM_PROGRAM")
    if not term_program:
        return
    app = TERM_PROGRAM_TO_APP.get(term_program.lower())
    if not app:
        return
    config = get_global_config()
    if config.get("deepLinkTerminal") == app:
        return
    save_global_config(lambda current: {**current, "deepLinkTerminal": app})
    logForDebugging(f"Stored deep link terminal preference: {app}")


update_deep_link_terminal_preference = updateDeepLinkTerminalPreference

