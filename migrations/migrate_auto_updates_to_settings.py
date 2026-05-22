"""Migration: Move autoUpdates preference to settings.json env var.

Mirrors src/migrations/migrateAutoUpdatesToSettings.ts.
"""
from __future__ import annotations

import json
from pathlib import Path


def migrate_auto_updates_to_settings() -> None:
    config_path = Path.home() / ".vivian" / "config.json"
    settings_path = Path.home() / ".vivian" / "settings.json"
    try:
        config = json.loads(config_path.read_text())
        if config.get("autoUpdates") is not False or config.get("autoUpdatesProtectedForNative") is True:
            return
        settings: dict = {}
        try:
            settings = json.loads(settings_path.read_text())
        except Exception:
            pass
        env = settings.get("env", {})
        env["DISABLE_AUTOUPDATER"] = "1"
        settings["env"] = env
        settings_path.write_text(json.dumps(settings, indent=2))
    except Exception:
        pass
