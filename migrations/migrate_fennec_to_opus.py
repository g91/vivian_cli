"""Migration: Rename 'fennec' model alias to 'opus' in settings.

Mirrors src/migrations/migrateFennecToOpus.ts.
"""
from __future__ import annotations

import json
from pathlib import Path

_FENNEC_ALIASES = {"vivian-opus-3", "vivian-3-opus", "fennec"}


def migrate_fennec_to_opus() -> None:
    settings_path = Path.home() / ".vivian" / "settings.json"
    try:
        settings = json.loads(settings_path.read_text())
        if settings.get("model") in _FENNEC_ALIASES:
            settings["model"] = "opus"
            settings_path.write_text(json.dumps(settings, indent=2))
    except Exception:
        pass
