"""Migration: Remap vivian-sonnet-1m to vivian-sonnet-4-5 in settings.

Mirrors src/migrations/migrateSonnet1mToSonnet45.ts.
"""
from __future__ import annotations

import json
from pathlib import Path

_SONNET_1M_MODELS = {"vivian-sonnet-1m", "vivian-sonnet-4-1m", "sonnet-1m"}


def migrate_sonnet_1m_to_sonnet_45() -> None:
    settings_path = Path.home() / ".vivian" / "settings.json"
    try:
        settings = json.loads(settings_path.read_text())
        if settings.get("model") in _SONNET_1M_MODELS:
            settings["model"] = "vivian-sonnet-4-5"
            settings_path.write_text(json.dumps(settings, indent=2))
    except Exception:
        pass
