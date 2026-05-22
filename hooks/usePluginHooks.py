"""Plugin hooks — mirrors src/hooks/usePluginHooks.ts."""
from __future__ import annotations
from typing import Any

def usePluginHooks() -> dict[str, Any]:
    """Plugin extension system."""
    hooks = {}
    return {"hooks": hooks, "register": lambda name, fn: None}

use_plugin_hooks = usePluginHooks
