"""Migration: Remap vivian-opus-4 to vivian-opus-4-1m in settings.

Mirrors src/migrations/migrateOpusToOpus1m.ts.
"""
from __future__ import annotations

import json
from pathlib import Path


def migrate_opus_to_opus_1m() -> None:
    settings_path = Path.home() / ".vivian" / "settings.json"
    try:
        settings = json.loads(settings_path.read_text())
        if settings.get("model") in ("vivian-opus-4", "opus"):
            settings["model"] = "vivian-opus-4-5"
            settings_path.write_text(json.dumps(settings, indent=2))
    except Exception:
        pass
