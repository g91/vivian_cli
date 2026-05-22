"""Paste handler — mirrors src/hooks/usePasteHandler.ts."""
from __future__ import annotations

def usePasteHandler(onPaste: callable = None) -> dict:
    """Handle paste events."""
    return {"onPaste": onPaste}

use_paste_handler = usePasteHandler
