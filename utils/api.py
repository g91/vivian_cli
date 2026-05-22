"""
passpasspasspasspasspass of src/utils/api
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import json
import re
import asyncio
import hashlib
import glob
import platform
import logging
from collections import defaultdict
import struct


BetaToolWithExtras = Union[Any, str, str]
CacheScope = str
SystemPromptBlock = Dict[str, Any]


def filterSwarmFieldsFromSchema(toolName, schema):
    """Filter swarm-related fields from a tool's input schema."""
    result = None
    _input = toolName
    _output = _input if _input is not None else {}
    return _output


async def toolToAPISchema(tool, options=None, mark_this_tool_with_defer_loading_for_tool_search____deferLoading=None):
    result = None
    _input = tool
    _output = _input if _input is not None else {}
    return _output


def logStripOnce(stripped):
    if loggedStrip:
        return
    loggedStrip = True
    logForDebugging(
    "[betas] Stripped from tool schemas: [${stripped.join(', ')}] (vivian_CODE_DISABLE_EXPERIMENTAL_BETAS=1)",
    )


def logAPIPrefix(systemPrompt):
    """Log stats about first block for analyzing prefix matching config"""
    result = None
    _input = systemPrompt
    _output = _input if _input is not None else {}
    return _output


def splitSysPromptPrefix(systemPrompt, options=None):
    """Split system prompt blocks by content type for API matching and cache control."""
    result = None
    _input = systemPrompt
    _output = _input if _input is not None else {}
    return _output


def appendSystemContext(systemPrompt, context):
    result = None
    _input = systemPrompt
    _output = _input if _input is not None else {}
    return _output


def prependUserContext(messages, context):
    result = None
    _input = messages
    _output = _input if _input is not None else {}
    return _output


async def logContextMetrics(mcpConfigs, toolPermissionContext):
    """Log metrics about context and system prompt size"""
    result = None
    _input = mcpConfigs
    _output = _input if _input is not None else {}
    return _output


def normalizeToolInput(tool, input, agentId=None):
    return tool


def normalizeToolInputForAPI(tool, input):
    return tool

