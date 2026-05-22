"""Migration: Remap legacy Opus 4.0/4.1 model strings to 'opus'.

Mirrors src/migrations/migrateLegacyOpusToCurrent.ts.
"""
from __future__ import annotations

import json
from pathlib import Path

_LEGACY_OPUS_MODELS = {
    "vivian-opus-4-20250514",
    "vivian-opus-4-1-20250805",
    "vivian-opus-4-0",
    "vivian-opus-4-1",
}


def migrate_legacy_opus_to_current() -> None:
    settings_path = Path.home() / ".vivian" / "settings.json"
    try:
        settings = json.loads(settings_path.read_text())
        if settings.get("model") in _LEGACY_OPUS_MODELS:
            settings["model"] = "opus"
            settings_path.write_text(json.dumps(settings, indent=2))
    except Exception:
        pass
