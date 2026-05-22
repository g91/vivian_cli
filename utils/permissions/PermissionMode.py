"""Port of src/utils/permissions/PermissionMode.ts"""
from __future__ import annotations
from typing import Literal, List, Optional, Dict

PERMISSION_MODES = ('default', 'acceptEdits', 'plan', 'bypassPermissions', 'auto', 'dontAsk')
EXTERNAL_PERMISSION_MODES = ('default', 'acceptEdits', 'plan', 'bypassPermissions')

PermissionMode = Literal['default', 'acceptEdits', 'plan', 'bypassPermissions', 'auto', 'dontAsk']
ExternalPermissionMode = Literal['default', 'acceptEdits', 'plan', 'bypassPermissions']

_PERMISSION_MODE_CONFIG: Dict[str, Dict[str, str]] = {
    'default': {'title': 'Default', 'shortTitle': 'Default', 'symbol': '', 'external': 'default'},
    'acceptEdits': {'title': 'Auto-edit', 'shortTitle': 'Auto-edit', 'symbol': 'E', 'external': 'acceptEdits'},
    'plan': {'title': 'Plan', 'shortTitle': 'Plan', 'symbol': 'P', 'external': 'plan'},
    'bypassPermissions': {'title': 'Auto-approve', 'shortTitle': 'Auto', 'symbol': 'Y', 'external': 'bypassPermissions'},
    'auto': {'title': 'Auto', 'shortTitle': 'Auto', 'symbol': 'A', 'external': 'default'},
    'dontAsk': {'title': 'Do not ask', 'shortTitle': "Don't ask", 'symbol': 'D', 'external': 'default'},
}


def permissionModeTitle(mode: str) -> str:
    """Get the human-readable title for a permission mode."""
    config = _PERMISSION_MODE_CONFIG.get(mode)
    return config['title'] if config else mode


def permissionModeShortTitle(mode: str) -> str:
    """Get the short title for a permission mode (used in status bar)."""
    config = _PERMISSION_MODE_CONFIG.get(mode)
    return config['shortTitle'] if config else mode


def permissionModeSymbol(mode: str) -> str:
    """Get the symbol character for a permission mode."""
    config = _PERMISSION_MODE_CONFIG.get(mode)
    return config['symbol'] if config else ''


def toExternalPermissionMode(mode: str) -> str:
    """Convert an internal permission mode to its external API equivalent."""
    config = _PERMISSION_MODE_CONFIG.get(mode)
    return config['external'] if config else 'default'
