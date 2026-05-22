"""Outside click — mirrors src/hooks/useOutsideClick.ts."""
from __future__ import annotations

def useOutsideClick(ref: Any = None, handler: callable = None) -> dict:
    """Detect clicks outside element."""
    return {"ref": ref, "handler": handler}

use_outside_click = useOutsideClick
