"""Migration: Move bypassPermissionsAccepted to settings.json.

Mirrors src/migrations/migrateBypassPermissionsAcceptedToSettings.ts.
"""
from __future__ import annotations

import json
from pathlib import Path


def migrate_bypass_permissions_accepted_to_settings() -> None:
    config_path = Path.home() / ".vivian" / "config.json"
    settings_path = Path.home() / ".vivian" / "settings.json"
    try:
        config = json.loads(config_path.read_text())
        val = config.get("bypassPermissionsAccepted")
        if val is None:
            return
        settings: dict = {}
        try:
            settings = json.loads(settings_path.read_text())
        except Exception:
            pass
        settings["bypassPermissionsAccepted"] = val
        settings_path.write_text(json.dumps(settings, indent=2))
        config.pop("bypassPermissionsAccepted", None)
        config_path.write_text(json.dumps(config, indent=2))
    except Exception:
        pass
