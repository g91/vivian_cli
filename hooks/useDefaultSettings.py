"""Default settings — mirrors src/hooks/useDefaultSettings.ts."""
from __future__ import annotations
from typing import Any

def useDefaultSettings() -> dict[str, Any]:
    """Get default application settings."""
    return {
        "theme": "light",
        "language": "en",
        "fontSize": 14,
        "fontFamily": "monospace",
    }

use_default_settings = useDefaultSettings
