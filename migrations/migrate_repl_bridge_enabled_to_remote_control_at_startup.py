"""Migration: Move replBridgeEnabled flag to remoteControlAtStartup.

Mirrors src/migrations/migrateReplBridgeEnabledToRemoteControlAtStartup.ts.
"""
from __future__ import annotations

import json
from pathlib import Path


def migrate_repl_bridge_enabled_to_remote_control_at_startup() -> None:
    config_path = Path.home() / ".vivian" / "config.json"
    settings_path = Path.home() / ".vivian" / "settings.json"
    try:
        config = json.loads(config_path.read_text())
        val = config.get("replBridgeEnabled")
        if val is None:
            return
        settings: dict = {}
        try:
            settings = json.loads(settings_path.read_text())
        except Exception:
            pass
        settings["remoteControlAtStartup"] = val
        settings_path.write_text(json.dumps(settings, indent=2))
        config.pop("replBridgeEnabled", None)
        config_path.write_text(json.dumps(config, indent=2))
    except Exception:
        pass
