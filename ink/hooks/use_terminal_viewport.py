"""Port of src/ink/hooks/use-terminal-viewport.ts."""
from __future__ import annotations

from typing import Any


def useTerminalViewport() -> dict[str, int]:
    """Get the current terminal viewport dimensions."""
    import shutil
    size = shutil.get_terminal_size()
    return {"width": size.columns, "height": size.lines}


use_terminal_viewport = useTerminalViewport
