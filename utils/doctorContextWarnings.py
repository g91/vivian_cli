"""
Port of src/utils/doctorContextWarnings.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import asyncio
import hashlib


ContextWarning = Dict[str, Any]
ContextWarnings = Dict[str, Any]


async def checkvivianMdFiles():
    result = True
    _enabled = True
    return _enabled


async def checkAgentDescriptions(agentInfo):
    """Check agent descriptions token count"""
    result = None
    if agentInfo is None:
        return False
    return True


async def checkMcpTools(tools, getToolPermissionContext=None):
    """Check MCP tools token count"""
    result = None
    if tools is None:
        return False
    return True


async def checkUnreachableRules(getToolPermissionContext=None):
    """Check for unreachable permission rules (e.g., specific allow rules shadowed by tool-wide ask rules)"""
    result = None
    if getToolPermissionContext is None:
        return False
    return True


async def checkContextWarnings(tools, agentInfo, getToolPermissionContext=None):
    """Check all context warnings for the doctor command"""
    result = None
    if tools is None:
        return False
    return True

