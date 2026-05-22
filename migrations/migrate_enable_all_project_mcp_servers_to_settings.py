"""Migration: Enable all project MCP servers to settings.

Mirrors src/migrations/migrateEnableAllProjectMcpServersToSettings.ts.
"""
from __future__ import annotations

import json
from pathlib import Path


def migrate_enable_all_project_mcp_servers_to_settings() -> None:
    config_path = Path.home() / ".vivian" / "config.json"
    settings_path = Path.home() / ".vivian" / "settings.json"
    try:
        config = json.loads(config_path.read_text())
        val = config.get("enableAllProjectMcpServers")
        if val is None:
            return
        settings: dict = {}
        try:
            settings = json.loads(settings_path.read_text())
        except Exception:
            pass
        settings["enableAllProjectMcpServers"] = val
        settings_path.write_text(json.dumps(settings, indent=2))
        config.pop("enableAllProjectMcpServers", None)
        config_path.write_text(json.dumps(config, indent=2))
    except Exception:
        pass
