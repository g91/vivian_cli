"""Port of src/ink/clearTerminal.ts."""
from __future__ import annotations

import os
import sys

from .termio.csi import CURSOR_HOME, csi, ERASE_SCREEN, ERASE_SCROLLBACK

CURSOR_HOME_WINDOWS = csi(0, "f")


def _is_windows_terminal() -> bool:
    return sys.platform == "win32" and bool(os.environ.get("WT_SESSION"))


def _is_mintty() -> bool:
    if os.environ.get("TERM_PROGRAM") == "mintty":
        return True
    if sys.platform == "win32" and os.environ.get("MSYSTEM"):
        return True
    return False


def _is_modern_windows_terminal() -> bool:
    if _is_windows_terminal():
        return True
    if (
        sys.platform == "win32"
        and os.environ.get("TERM_PROGRAM") == "vscode"
        and os.environ.get("TERM_PROGRAM_VERSION")
    ):
        return True
    if _is_mintty():
        return True
    return False


def getClearTerminalSequence() -> str:
    if sys.platform == "win32":
        if _is_modern_windows_terminal():
            return ERASE_SCREEN + ERASE_SCROLLBACK + CURSOR_HOME
        else:
            return ERASE_SCREEN + CURSOR_HOME_WINDOWS
    return ERASE_SCREEN + ERASE_SCROLLBACK + CURSOR_HOME


clearTerminal = getClearTerminalSequence()
get_clear_terminal_sequence = getClearTerminalSequence
