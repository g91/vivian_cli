"""IDE integration — mirrors src/hooks/useIDEIntegration.ts."""
from __future__ import annotations

def useIDEIntegration() -> dict:
    """IDE integration layer."""
    return {"connected": True}

use_ide_integration = useIDEIntegration
