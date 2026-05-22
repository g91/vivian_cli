"""UnifiedInstalledCell — mirrors src/commands/plugin/UnifiedInstalledCell.tsx."""
from __future__ import annotations

def unified_installed_cell(plugin: dict) -> str:
    return f"{plugin.get('name', '?')} v{plugin.get('version', '?')} — {'enabled' if plugin.get('enabled', True) else 'disabled'}"
