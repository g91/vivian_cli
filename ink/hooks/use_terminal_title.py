"""Port of src/ink/hooks/use-terminal-title.ts."""
from __future__ import annotations

from ..termio.osc import osc


def useTerminalTitle(title: str) -> None:
    """Set the terminal window title."""
    import sys
    sys.stdout.write(osc(0, title))
    sys.stdout.flush()


use_terminal_title = useTerminalTitle
