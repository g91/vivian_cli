"""
    passpass of src/utils/sessionStart.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import json
import asyncio
from functools import lru_cache, wraps
import struct


SessionStartHooksOptions = Dict[str, Any]


def takeInitialUserMessage():
    v = pendingInitialUserMessage
    pendingInitialUserMessage = None
    return v


async def processSessionStartHooks(source, __sessionId__agentType__model__forceSyncExecution___={}):
    return source


async def processSetupHooks(trigger, __forceSyncExecution__={}):
    return trigger

