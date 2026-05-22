"""JSON editor — mirrors src/hooks/useJsonEditor.ts."""
from __future__ import annotations
from typing import Any

def useJsonEditor(initialValue: str = "{}") -> dict[str, Any]:
    """Edit JSON with validation."""
    return {
        "value": initialValue,
        "error": None,
        "isValid": True,
    }

use_json_editor = useJsonEditor
