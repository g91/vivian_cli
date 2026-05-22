"""
Port of src/utils/toolSearch
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import os
import os.path
import json
import asyncio
import hashlib
import math
from collections import defaultdict
from functools import lru_cache, wraps
import struct

from ..services.analytics.growthbook import getFeatureValue_CACHED_MAY_BE_STALE
from ..constants.tools import TOOL_SEARCH_TOOL_NAME
from .betas import CONTEXT_1M_BETA_HEADER, get_beta_headers
from .debug import logForDebugging
from .envUtils import is_env_defined_falsy, is_env_truthy
from .model.providers import getAPIProvider, isFirstPartyAnthropicBaseUrl
from .model.modelCapabilities import getModelCapability
from ..services.analytics.index import logEvent
from .analyzeContext import countToolDefinitionTokens, TOOL_TOKEN_COUNT_OVERHEAD


ToolSearchMode = str
ToolResultBlock = Dict[str, Any]
DeferredToolsDelta = Dict[str, Any]
DeferredToolsDeltaScanContext = Dict[str, Any]

DEFAULT_UNSUPPORTED_MODEL_PATTERNS = ['haiku']
DEFAULT_AUTO_TOOL_SEARCH_PERCENTAGE = 10
CHARS_PER_TOKEN = 2.5
MODEL_CONTEXT_WINDOW_DEFAULT = 200_000
loggedOptimistic = False
_deferred_tool_token_count_cache = {}


def parseAutoPercentage(value):
    """Parse auto:N syntax from ENABLE_TOOL_SEARCH env var."""
    if not str(value).startswith('auto:'):
        return None

    percent_str = str(value)[5:]

    try:
        percent = int(percent_str, 10)
    except ValueError:
        logForDebugging(
            f'Invalid ENABLE_TOOL_SEARCH value "{value}": expected auto:N where N is a number.'
        )
        return None

    return max(0, min(100, percent))


def isAutoToolSearchMode(value):
    """Check if ENABLE_TOOL_SEARCH is set to auto mode (auto or auto:N)."""
    if not value:
        return False
    return value == 'auto' or str(value).startswith('auto:')


def getAutoToolSearchPercentage():
    """Get the auto-enable percentage from env var or default."""
    value = os.environ.get('ENABLE_TOOL_SEARCH')
    if not value or value == 'auto':
        return DEFAULT_AUTO_TOOL_SEARCH_PERCENTAGE

    parsed = parseAutoPercentage(value)
    if parsed is not None:
        return parsed
    return DEFAULT_AUTO_TOOL_SEARCH_PERCENTAGE


def getAutoToolSearchTokenThreshold(model):
    """Get the token threshold for auto-enabling tool search for a given model."""
    context_window = _get_context_window_for_tool_search(model)
    percentage = getAutoToolSearchPercentage() / 100
    return math.floor(context_window * percentage)


def getAutoToolSearchCharThreshold(model):
    """Get the character threshold for auto-enabling tool search for a given model."""
    return math.floor(getAutoToolSearchTokenThreshold(model) * CHARS_PER_TOKEN)


def getToolSearchMode():
    """Determines the tool search mode from ENABLE_TOOL_SEARCH."""
    if is_env_truthy(os.environ.get('vivian_CODE_DISABLE_EXPERIMENTAL_BETAS')):
        return 'standard'

    value = os.environ.get('ENABLE_TOOL_SEARCH')
    auto_percent = parseAutoPercentage(value) if value else None
    if auto_percent == 0:
        return 'tst'
    if auto_percent == 100:
        return 'standard'
    if isAutoToolSearchMode(value):
        return 'tst-auto'

    if is_env_truthy(value):
        return 'tst'
    if is_env_defined_falsy(os.environ.get('ENABLE_TOOL_SEARCH')):
        return 'standard'
    return 'tst'


parse_auto_percentage = parseAutoPercentage
is_auto_tool_search_mode = isAutoToolSearchMode
get_auto_tool_search_percentage = getAutoToolSearchPercentage
get_tool_search_mode = getToolSearchMode
get_auto_tool_search_token_threshold = getAutoToolSearchTokenThreshold
get_auto_tool_search_char_threshold = getAutoToolSearchCharThreshold


def _get_context_window_for_tool_search(model):
    if os.environ.get('USER_TYPE') == 'ant' and os.environ.get('vivian_CODE_MAX_CONTEXT_TOKENS'):
        try:
            override = int(os.environ['vivian_CODE_MAX_CONTEXT_TOKENS'], 10)
        except ValueError:
            override = 0
        if override > 0:
            return override

    normalized_model = str(model or '').lower()
    if not is_env_truthy(os.environ.get('vivian_CODE_DISABLE_1M_CONTEXT')) and '[1m]' in normalized_model:
        return 1_000_000

    capability = getModelCapability(model)
    max_input_tokens = capability.get('max_input_tokens') if isinstance(capability, dict) else None
    if isinstance(max_input_tokens, int) and max_input_tokens >= 100_000:
        if max_input_tokens > MODEL_CONTEXT_WINDOW_DEFAULT and is_env_truthy(
            os.environ.get('vivian_CODE_DISABLE_1M_CONTEXT')
        ):
            return MODEL_CONTEXT_WINDOW_DEFAULT
        return max_input_tokens

    betas = get_beta_headers(model=model)
    if (
        not is_env_truthy(os.environ.get('vivian_CODE_DISABLE_1M_CONTEXT'))
        and CONTEXT_1M_BETA_HEADER in betas
        and ('vivian-sonnet-4' in normalized_model or 'opus-4-6' in normalized_model)
    ):
        return 1_000_000

    return MODEL_CONTEXT_WINDOW_DEFAULT


def getUnsupportedToolReferencePatterns():
    """Get the list of model patterns that do NOT support tool_reference."""
    try:
        patterns = getFeatureValue_CACHED_MAY_BE_STALE(
            'tengu_tool_search_unsupported_models',
            None,
        )
        if isinstance(patterns, list) and len(patterns) > 0:
            return patterns
    except Exception:
        pass
    return DEFAULT_UNSUPPORTED_MODEL_PATTERNS


def modelSupportsToolReference(model):
    """Check if a model supports tool_reference blocks (required for tool search)."""
    if model is None:
        return False
    normalized_model = str(model).lower()
    for pattern in getUnsupportedToolReferencePatterns():
        if str(pattern).lower() in normalized_model:
            return False
    return True


get_unsupported_tool_reference_patterns = getUnsupportedToolReferencePatterns
model_supports_tool_reference = modelSupportsToolReference


def isToolSearchEnabledOptimistic():
    global loggedOptimistic

    mode = getToolSearchMode()
    if mode == 'standard':
        if not loggedOptimistic:
            loggedOptimistic = True
            logForDebugging(
                f'[ToolSearch:optimistic] mode={mode}, ENABLE_TOOL_SEARCH={os.environ.get("ENABLE_TOOL_SEARCH")}, result=false'
            )
        return False

    if (
        not os.environ.get('ENABLE_TOOL_SEARCH')
        and getAPIProvider() == 'firstParty'
        and not isFirstPartyAnthropicBaseUrl()
    ):
        if not loggedOptimistic:
            loggedOptimistic = True
            logForDebugging(
                '[ToolSearch:optimistic] disabled: ANTHROPIC_BASE_URL='
                f'{os.environ.get("ANTHROPIC_BASE_URL")} is not a first-party Anthropic host. '
                'Set ENABLE_TOOL_SEARCH=true (or auto / auto:N) if your proxy forwards tool_reference blocks.'
            )
        return False

    if not loggedOptimistic:
        loggedOptimistic = True
        logForDebugging(
            f'[ToolSearch:optimistic] mode={mode}, ENABLE_TOOL_SEARCH={os.environ.get("ENABLE_TOOL_SEARCH")}, result=true'
        )
    return True


def isToolSearchToolAvailable(tools):
    """Check if ToolSearchTool is available in the provided tools list."""
    for tool in tools or []:
        if isinstance(tool, dict) and tool.get('name') == TOOL_SEARCH_TOOL_NAME:
            return True
        if getattr(tool, 'name', None) == TOOL_SEARCH_TOOL_NAME:
            return True
    return False


is_tool_search_enabled_optimistic = isToolSearchEnabledOptimistic
is_tool_search_tool_available = isToolSearchToolAvailable


async def calculateDeferredToolDescriptionChars(tools, getToolPermissionContext=None):
    """Calculate total deferred tool description size in characters."""
    deferred_tools = [tool for tool in (tools or []) if _is_deferred_tool_for_delta(tool)]
    if not deferred_tools:
        return 0

    sizes = await asyncio.gather(
        *[
            _calculate_deferred_tool_size(tool, tools or [], getToolPermissionContext)
            for tool in deferred_tools
        ]
    )
    return sum(sizes)


async def isToolSearchEnabled(model, tools, getToolPermissionContext=None):
    """Check if tool search (MCP tool deferral with tool_reference) is enabled for a specific request."""
    if model is None:
        return False

    mcp_tool_count = sum(1 for tool in (tools or []) if _tool_flag(tool, 'isMcp') is True)

    def log_mode_decision(enabled, mode, reason, extra_props=None):
        payload = {
            'enabled': bool(enabled),
            'mode': mode,
            'reason': reason,
            'checkedModel': str(model),
            'mcpToolCount': mcp_tool_count,
            'userType': os.environ.get('USER_TYPE') or 'external',
        }
        if isinstance(extra_props, dict):
            payload.update(extra_props)
        logEvent('tengu_tool_search_mode_decision', payload)

    if not modelSupportsToolReference(model):
        logForDebugging(
            f"Tool search disabled for model '{model}': model does not support tool_reference blocks. "
            'This feature is only available on vivian Sonnet 4+, Opus 4+, and newer models.'
        )
        log_mode_decision(False, 'standard', 'model_unsupported')
        return False

    if not isToolSearchToolAvailable(tools):
        logForDebugging(
            'Tool search disabled: ToolSearchTool is not available '
            '(may have been disallowed via disallowedTools).'
        )
        log_mode_decision(False, 'standard', 'mcp_search_unavailable')
        return False

    mode = getToolSearchMode()
    if mode == 'tst':
        log_mode_decision(True, mode, 'tst_enabled')
        return True

    if mode == 'tst-auto':
        threshold_result = await checkAutoThreshold(tools, getToolPermissionContext, model)
        debug_description = threshold_result.get('debugDescription', '')
        if threshold_result.get('enabled'):
            logForDebugging(f'Auto tool search enabled: {debug_description}')
            log_mode_decision(True, mode, 'auto_above_threshold', threshold_result.get('metrics'))
            return True

        logForDebugging(f'Auto tool search disabled: {debug_description}')
        log_mode_decision(False, mode, 'auto_below_threshold', threshold_result.get('metrics'))
        return False

    log_mode_decision(False, mode, 'standard_mode')
    return False


def isToolReferenceBlock(obj):
    """Check if an object is a tool_reference block."""
    return isinstance(obj, dict) and obj.get('type') == 'tool_reference'


def isToolReferenceWithName(obj):
    """Type guard for tool_reference block with tool_name."""
    return isToolReferenceBlock(obj) and isinstance(obj.get('tool_name'), str)


def isToolResultBlockWithContent(obj):
    """Type guard for tool_result blocks with array content."""
    return isinstance(obj, dict) and obj.get('type') == 'tool_result' and isinstance(obj.get('content'), list)


is_tool_reference_block = isToolReferenceBlock
is_tool_reference_with_name = isToolReferenceWithName
is_tool_result_block_with_content = isToolResultBlockWithContent


def extractDiscoveredToolNames(messages):
    """Extract tool names from tool_reference blocks in message history."""
    discovered_tools = set()
    carried_from_boundary = 0

    for message in messages or []:
        if (
            isinstance(message, dict)
            and message.get('type') == 'system'
            and message.get('subtype') == 'compact_boundary'
        ):
            compact_metadata = message.get('compactMetadata') or {}
            carried = compact_metadata.get('preCompactDiscoveredTools') or []
            for name in carried:
                discovered_tools.add(name)
            carried_from_boundary += len(carried)
            continue

        if not isinstance(message, dict) or message.get('type') != 'user':
            continue

        content = ((message.get('message') or {}).get('content'))
        if not isinstance(content, list):
            continue

        for block in content:
            if isToolResultBlockWithContent(block):
                for item in block.get('content', []):
                    if isToolReferenceWithName(item):
                        discovered_tools.add(item['tool_name'])

    if discovered_tools:
        suffix = (
            f' ({carried_from_boundary} carried from compact boundary)'
            if carried_from_boundary > 0
            else ''
        )
        logForDebugging(
            f'Dynamic tool loading: found {len(discovered_tools)} discovered tools in message history{suffix}'
        )

    return discovered_tools


extract_discovered_tool_names = extractDiscoveredToolNames


def isDeferredToolsDeltaEnabled():
    """True -> announce deferred tools via persisted delta attachments."""
    return os.environ.get('USER_TYPE') == 'ant' or bool(
        getFeatureValue_CACHED_MAY_BE_STALE('tengu_glacier_2xr', False)
    )


is_deferred_tools_delta_enabled = isDeferredToolsDeltaEnabled


def getDeferredToolsDelta(tools, messages, scanContext=None):
    """Diff the current deferred-tool pool against what's already been"""
    announced = set()
    attachment_count = 0
    dtd_count = 0
    attachment_types_seen = set()

    for message in messages or []:
        if not isinstance(message, dict) or message.get('type') != 'attachment':
            continue
        attachment_count += 1
        attachment = message.get('attachment') or {}
        attachment_type = attachment.get('type')
        if isinstance(attachment_type, str):
            attachment_types_seen.add(attachment_type)
        if attachment_type != 'deferred_tools_delta':
            continue
        dtd_count += 1
        for name in attachment.get('addedNames') or []:
            announced.add(name)
        for name in attachment.get('removedNames') or []:
            announced.discard(name)

    deferred = [tool for tool in (tools or []) if _is_deferred_tool_for_delta(tool)]
    deferred_names = { _tool_name(tool) for tool in deferred if _tool_name(tool) }
    pool_names = { _tool_name(tool) for tool in (tools or []) if _tool_name(tool) }

    added = [tool for tool in deferred if _tool_name(tool) not in announced]
    removed = []
    for name in announced:
        if name in deferred_names:
            continue
        if name not in pool_names:
            removed.append(name)

    if not added and not removed:
        return None

    logEvent(
        'tengu_deferred_tools_pool_change',
        {
            'addedCount': len(added),
            'removedCount': len(removed),
            'priorAnnouncedCount': len(announced),
            'messagesLength': len(messages or []),
            'attachmentCount': attachment_count,
            'dtdCount': dtd_count,
            'callSite': (scanContext or {}).get('callSite', 'unknown'),
            'querySource': (scanContext or {}).get('querySource', 'unknown'),
            'attachmentTypesSeen': ','.join(sorted(attachment_types_seen)),
        },
    )

    return {
        'addedNames': sorted([_tool_name(tool) for tool in added if _tool_name(tool)]),
        'addedLines': sorted([_format_deferred_tool_line(tool) for tool in added]),
        'removedNames': sorted(removed),
    }


def _tool_name(tool):
    if isinstance(tool, dict):
        return tool.get('name')
    return getattr(tool, 'name', None)


def _tool_flag(tool, name):
    if isinstance(tool, dict):
        return tool.get(name)
    return getattr(tool, name, None)


def _is_deferred_tool_for_delta(tool):
    if _tool_flag(tool, 'alwaysLoad') is True:
        return False
    if _tool_flag(tool, 'isMcp') is True:
        return True
    if _tool_name(tool) == TOOL_SEARCH_TOOL_NAME:
        return False
    return _tool_flag(tool, 'shouldDefer') is True


def _format_deferred_tool_line(tool):
    return str(_tool_name(tool) or '')


async def _calculate_deferred_tool_size(tool, tools, getToolPermissionContext):
    description = await _get_tool_prompt_text(tool, tools, getToolPermissionContext)
    input_schema_text = _get_tool_schema_text(tool)
    return len(str(_tool_name(tool) or '')) + len(description) + len(input_schema_text)


async def _get_tool_prompt_text(tool, tools, getToolPermissionContext):
    prompt_fn = None
    if isinstance(tool, dict):
        prompt_fn = tool.get('prompt')
    else:
        prompt_fn = getattr(tool, 'prompt', None)

    if not callable(prompt_fn):
        return ''

    context = {
        'getToolPermissionContext': getToolPermissionContext,
        'tools': tools,
        'agents': [],
    }
    try:
        return await prompt_fn(context)
    except TypeError:
        try:
            return await prompt_fn()
        except TypeError:
            return ''


def _get_tool_schema_text(tool):
    schema = None
    if isinstance(tool, dict):
        schema = tool.get('inputJSONSchema') or tool.get('input_schema') or tool.get('INPUT_SCHEMA')
    else:
        schema = (
            getattr(tool, 'inputJSONSchema', None)
            or getattr(tool, 'input_schema', None)
            or getattr(tool, 'INPUT_SCHEMA', None)
        )

    if not schema:
        return ''
    try:
        return json.dumps(schema, sort_keys=True)
    except TypeError:
        return str(schema)


calculate_deferred_tool_description_chars = calculateDeferredToolDescriptionChars
is_tool_search_enabled = isToolSearchEnabled


get_deferred_tools_delta = getDeferredToolsDelta


async def checkAutoThreshold(tools, getToolPermissionContext=None, model=None):
    """Check whether deferred tools exceed the auto-threshold for enabling TST."""
    threshold_model = model or ''
    deferred_tool_tokens = await _get_deferred_tool_token_count(tools or [], getToolPermissionContext)
    if deferred_tool_tokens is not None:
        threshold = getAutoToolSearchTokenThreshold(threshold_model)
        return {
            'enabled': deferred_tool_tokens >= threshold,
            'debugDescription': (
                f'{deferred_tool_tokens} tokens (threshold: {threshold}, '
                f'{getAutoToolSearchPercentage()}% of context)'
            ),
            'metrics': {
                'deferredToolTokens': deferred_tool_tokens,
                'threshold': threshold,
            },
        }

    deferred_tool_description_chars = await calculateDeferredToolDescriptionChars(
        tools or [],
        getToolPermissionContext,
    )
    char_threshold = getAutoToolSearchCharThreshold(threshold_model)
    return {
        'enabled': deferred_tool_description_chars >= char_threshold,
        'debugDescription': (
            f'{deferred_tool_description_chars} chars (threshold: {char_threshold}, '
            f'{getAutoToolSearchPercentage()}% of context) (char fallback)'
        ),
        'metrics': {
            'deferredToolDescriptionChars': deferred_tool_description_chars,
            'charThreshold': char_threshold,
        },
    }


async def _get_deferred_tool_token_count(tools, getToolPermissionContext=None):
    deferred_tools = [tool for tool in (tools or []) if _is_deferred_tool_for_delta(tool)]
    if not deferred_tools:
        return 0

    cache_key = ','.join(sorted([_tool_name(tool) for tool in deferred_tools if _tool_name(tool)]))
    cached = _deferred_tool_token_count_cache.get(cache_key, None)
    if cache_key in _deferred_tool_token_count_cache:
        return cached

    try:
        total = await countToolDefinitionTokens(deferred_tools, getToolPermissionContext)
        if total == 0:
            result = None
        else:
            result = max(0, int(total) - int(TOOL_TOKEN_COUNT_OVERHEAD))
    except Exception:
        result = None

    _deferred_tool_token_count_cache[cache_key] = result
    return result


check_auto_threshold = checkAutoThreshold

