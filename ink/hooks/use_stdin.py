"""Port of src/ink/hooks/use-stdin.ts."""
from __future__ import annotations

from ..components.StdinContext import StdinContextProps, getStdinContext


def useStdin() -> StdinContextProps:
    """Get the current stdin context."""
    return getStdinContext()


use_stdin = useStdin
