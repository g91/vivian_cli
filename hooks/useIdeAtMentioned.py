"""IDE @ mention support — mirrors src/hooks/useIdeAtMentioned.ts."""
from __future__ import annotations

def useIdeAtMentioned() -> dict:
    """Handle @ mentions in IDE."""
    return {"available": True}

use_ide_at_mentioned = useIdeAtMentioned
