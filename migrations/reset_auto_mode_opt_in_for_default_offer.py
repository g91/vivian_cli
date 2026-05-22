"""Migration: Reset auto-mode opt-in for default offer.

Mirrors src/migrations/resetAutoModeOptInForDefaultOffer.ts.
"""
from __future__ import annotations

import json
from pathlib import Path


def reset_auto_mode_opt_in_for_default_offer() -> None:
    settings_path = Path.home() / ".vivian" / "settings.json"
    try:
        settings = json.loads(settings_path.read_text())
        if "autoModeOptIn" in settings:
            del settings["autoModeOptIn"]
            settings_path.write_text(json.dumps(settings, indent=2))
    except Exception:
        pass
