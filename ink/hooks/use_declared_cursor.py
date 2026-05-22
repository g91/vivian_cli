"""Port of src/ink/hooks/use-declared-cursor.ts."""
from __future__ import annotations

from typing import Any


def useDeclaredCursor() -> dict[str, Any] | None:
    """Get the declared cursor position."""
    return None


use_declared_cursor = useDeclaredCursor
