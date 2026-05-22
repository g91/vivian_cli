"""Migration: Remap vivian-sonnet-4-5 to vivian-sonnet-4-6 in settings.

Mirrors src/migrations/migrateSonnet45ToSonnet46.ts.
"""
from __future__ import annotations

import json
from pathlib import Path

_SONNET_45_MODELS = {"vivian-sonnet-4-5", "vivian-sonnet-4-5-20251101"}


def migrate_sonnet_45_to_sonnet_46() -> None:
    settings_path = Path.home() / ".vivian" / "settings.json"
    try:
        settings = json.loads(settings_path.read_text())
        if settings.get("model") in _SONNET_45_MODELS:
            settings["model"] = "vivian-sonnet-4-6"
            settings_path.write_text(json.dumps(settings, indent=2))
    except Exception:
        pass
