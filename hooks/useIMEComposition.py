"""IME composition — mirrors src/hooks/useIMEComposition.ts."""
from __future__ import annotations

def useIMEComposition() -> dict:
    """Handle IME text composition."""
    return {
        "isComposing": False,
        "compositionValue": "",
    }

use_ime_composition = useIMEComposition
