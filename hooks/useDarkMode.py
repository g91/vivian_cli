"""Dark mode state — mirrors src/hooks/useDarkMode.ts."""
from __future__ import annotations

def useDarkMode(enabled: bool | None = None) -> dict:
    """Manage dark mode preference."""
    return {
        "isDarkMode": enabled if enabled is not None else False,
        "toggle": lambda: None,
    }

use_dark_mode = useDarkMode
