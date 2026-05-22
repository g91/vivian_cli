"""Multi-line edit — mirrors src/hooks/useMultiLineEdit.ts."""
from __future__ import annotations

def useMultiLineEdit(initialValue: str = "") -> dict:
    """Multi-line text editing."""
    return {"value": initialValue, "lines": initialValue.split("\n")}

use_multi_line_edit = useMultiLineEdit
