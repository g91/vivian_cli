"""Plugin installation status — mirrors src/hooks/notifs/usePluginInstallationStatus.ts."""
from __future__ import annotations

def usePluginInstallationStatus(plugin: str = "") -> dict:
    """Display plugin installation status."""
    return {"plugin": plugin, "status": "installing"}

use_plugin_installation_status = usePluginInstallationStatus
