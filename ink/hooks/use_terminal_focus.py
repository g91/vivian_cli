"""Port of src/ink/hooks/use-terminal-focus.ts."""
from __future__ import annotations

from ..terminal_focus_state import getTerminalFocusState, subscribeTerminalFocus


def useTerminalFocus() -> bool:
    """Get whether the terminal is currently focused."""
    return getTerminalFocusState() != "blurred"


use_terminal_focus = useTerminalFocus
