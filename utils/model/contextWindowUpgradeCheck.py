"""Port of src/utils/model/contextWindowUpgradeCheck.ts"""
from __future__ import annotations

from typing import Optional

def _get_available_upgrade() -> Optional[dict]:
    try:
        from .model import getUserSpecifiedModelSetting
        from .check1mAccess import checkOpus1mAccess, checkSonnet1mAccess
        current = getUserSpecifiedModelSetting()
        if current == 'opus' and checkOpus1mAccess():
            return {'alias': 'opus[1m]', 'name': 'Opus 1M', 'multiplier': 5}
        if current == 'sonnet' and checkSonnet1mAccess():
            return {'alias': 'sonnet[1m]', 'name': 'Sonnet 1M', 'multiplier': 5}
    except Exception:
        pass
    return {}

def getUpgradeMessage(context: str) -> Optional[str]:
    upgrade = _get_available_upgrade()
    if not upgrade:
        return None
    if context == 'warning':
        return f"/model {upgrade['alias']}"
    if context == 'tip':
        return f"Tip: You have access to {upgrade['name']} with {upgrade['multiplier']}x more context"
    return None
