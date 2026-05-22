"""Port of src/utils/permissions/PermissionResult.ts"""
from __future__ import annotations
from typing import Optional, Dict, Any, Literal, Union, List

PermissionBehavior = Literal['allow', 'deny', 'ask']


def getRuleBehaviorDescription(permission_result: str) -> str:
    """Get the appropriate prose description for rule behavior."""
    if permission_result == 'allow':
        return 'allowed'
    if permission_result == 'deny':
        return 'denied'
    return 'asked for confirmation for'
