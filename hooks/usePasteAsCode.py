"""Paste as code — mirrors src/hooks/usePasteAsCode.ts."""
from __future__ import annotations

def usePasteAsCode(onPaste: callable = None) -> dict:
    """Handle pasted code."""
    return {"handling": False, "onPaste": onPaste}

use_paste_as_code = usePasteAsCode
