"""Layout preference — mirrors src/hooks/useLayoutPreference.ts."""
from __future__ import annotations

def useLayoutPreference(defaultLayout: str = "vertical") -> dict:
    """Manage UI layout preference."""
    return {
        "layout": defaultLayout,
        "setLayout": lambda l: None,
    }

use_layout_preference = useLayoutPreference
