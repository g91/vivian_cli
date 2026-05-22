"""Copy on select hook — mirrors src/hooks/useCopyOnSelect.ts."""
from __future__ import annotations

def useCopyOnSelect(enabled: bool = False) -> dict:
    """Enable copy-on-text-select behavior."""
    return {'enabled': enabled}

use_copy_on_select = useCopyOnSelect
