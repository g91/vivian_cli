"""Port of src/utils/permissions/PermissionRule.ts"""
from __future__ import annotations
from typing import Optional, Dict, Any, Literal, List, TypedDict

PermissionBehavior = Literal['allow', 'deny', 'ask']


class PermissionRuleValue(TypedDict, total=False):
    toolName: str
    ruleContent: str


class PermissionRule(TypedDict):
    source: str
    ruleBehavior: str
    ruleValue: PermissionRuleValue


PERMISSION_BEHAVIORS = ('allow', 'deny', 'ask')
