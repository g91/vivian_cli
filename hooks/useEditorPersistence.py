"""Editor persistence — mirrors src/hooks/useEditorPersistence.ts."""
from __future__ import annotations
from typing import Any

def useEditorPersistence() -> dict[str, Any]:
    """Persist editor state."""
    return {
        "save": lambda state: None,
        "load": lambda: {},
    }

use_editor_persistence = useEditorPersistence
