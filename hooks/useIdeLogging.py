"""IDE logging — mirrors src/hooks/useIdeLogging.ts."""
from __future__ import annotations

def useIdeLogging(level: str = "info") -> dict:
    """IDE logging integration."""
    return {"level": level}

use_ide_logging = useIdeLogging
