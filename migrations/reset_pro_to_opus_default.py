"""Migration: Reset Pro users back to Opus default model.

Mirrors src/migrations/resetProToOpusDefault.ts.
"""
from __future__ import annotations

import json
from pathlib import Path


def reset_pro_to_opus_default() -> None:
    settings_path = Path.home() / ".vivian" / "settings.json"
    config_path = Path.home() / ".vivian" / "config.json"
    try:
        config = json.loads(config_path.read_text())
        if not config.get("isPro"):
            return
        settings = json.loads(settings_path.read_text())
        if settings.get("model") == "sonnet":
            settings["model"] = "opus"
            settings_path.write_text(json.dumps(settings, indent=2))
    except Exception:
        pass
