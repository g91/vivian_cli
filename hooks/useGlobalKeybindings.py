"""Global keybindings — mirrors src/hooks/useGlobalKeybindings.ts."""
from __future__ import annotations

def useGlobalKeybindings() -> dict:
    """Register global keyboard bindings."""
    return {"bindings": {}}

use_global_keybindings = useGlobalKeybindings
