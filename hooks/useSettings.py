"""Port of src/hooks/useSettings.ts."""
from __future__ import annotations


def useSettings(app_state):
    if isinstance(app_state, dict):
        return app_state.get('settings', {})
    return getattr(app_state, 'settings', {})
