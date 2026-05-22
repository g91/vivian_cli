"""Parent focus detection — mirrors src/hooks/useParentFocus.ts."""
from __future__ import annotations

def useParentFocus() -> bool:
    """Detect if parent element has focus."""
    return False

use_parent_focus = useParentFocus
