"""Manage plugins — mirrors src/hooks/useManagePlugins.ts."""
from __future__ import annotations

def useManagePlugins() -> dict:
    """Plugin management."""
    return {"plugins": [], "install": lambda p: None, "remove": lambda p: None}

use_manage_plugins = useManagePlugins
