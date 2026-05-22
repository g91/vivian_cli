"""Ownership context — mirrors src/hooks/useOwnershipContext.ts."""
from __future__ import annotations

def useOwnershipContext() -> dict:
    """Manage ownership context."""
    return {"owner": None}

use_ownership_context = useOwnershipContext
