"""Portal — mirrors src/hooks/usePortal.ts."""
from __future__ import annotations

def usePortal(id: str = "portal") -> dict:
    """Create portal for rendering."""
    return {"id": id, "element": None}

use_portal = usePortal
