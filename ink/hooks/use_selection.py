"""Port of src/ink/hooks/use-selection.ts."""
from __future__ import annotations

from typing import Any


def useSelection() -> dict[str, Any]:
    """Get the current text selection state."""
    return {"hasSelection": False, "selectedText": ""}


use_selection = useSelection
