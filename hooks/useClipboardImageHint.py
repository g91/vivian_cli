"""Clipboard image hint — mirrors src/hooks/useClipboardImageHint.ts."""
from __future__ import annotations

async def useClipboardImageHint() -> dict | None:
    """Notify when image can be pasted from clipboard."""
    return {"type": "info", "message": "Image in clipboard. Use Ctrl+V to paste."}

use_clipboard_image_hint = useClipboardImageHint
