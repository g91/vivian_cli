"""Port of src/utils/permissions/PermissionUpdateSchema.ts"""
from __future__ import annotations
from typing import Optional, Dict, Any, Literal, List, TypedDict

PermissionUpdateDestination = Literal['localSettings', 'projectSettings', 'userSettings', 'session']


class PermissionUpdate(TypedDict, total=False):
    type: str
    rules: List[Dict[str, Any]]
    behavior: str
    destination: str
    toolName: str
    source: str
