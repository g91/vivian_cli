"""
passpasspasspasspasspasspasspasspasspass of src/utils/analyzeContext
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, TypedDict, Union

from ..Tool import findToolByName
from ..constants.tools import SKILL_TOOL_NAME
from ..services.tokenEstimation import (
    countMessagesTokensWithAPI,
    countTokensViaHaikuFallback,
    roughTokenCountEstimation,
)
from .debug import logError, logForDebugging
from .settings.constants import SettingSource
from .slowOperations import jsonStringify


MessageBreakdown = Dict[str, Any]


class ContextCategory(TypedDict, total=False):
    name: str
    tokens: float
    color: Any
    isDeferred: bool


class GridSquare(TypedDict, total=False):
    color: Any
    isFilled: bool
    categoryName: str
    tokens: float
    percentage: float
    squareFullness: Any


class MemoryFile(TypedDict, total=False):
    path: str
    type: str
    tokens: float


class McpTool(TypedDict, total=False):
    name: str
    serverName: str
    tokens: float
    isLoaded: bool


class DeferredBuiltinTool(TypedDict, total=False):
    name: str
    tokens: float
    isLoaded: bool


class SystemToolDetail(TypedDict, total=False):
    name: str
    tokens: float


class SystemPromptSectionDetail(TypedDict, total=False):
    name: str
    tokens: float


class Agent(TypedDict, total=False):
    agentType: str
    source: Union[SettingSource, str, str]
    tokens: float


class SlashCommandInfo(TypedDict, total=False):
    totalCommands: float
    includedCommands: float
    tokens: float


class SkillFrontmatter(TypedDict, total=False):
    name: str
    source: Union[SettingSource, str]
    tokens: float


class SkillInfo(TypedDict, total=False):
    """Information about skills included in the context window."""
    totalSkills: float
    includedSkills: float
    tokens: float
    skillFrontmatter: List[SkillFrontmatter]


class ContextData(TypedDict, total=False):
    categories: List[ContextCategory]
    totalTokens: float
    maxTokens: float
    rawMaxTokens: float
    percentage: float
    gridRows: List[List[GridSquare]]
    model: str
    memoryFiles: List[MemoryFile]
    mcpTools: List[McpTool]
    deferredBuiltinTools: List[DeferredBuiltinTool]
    systemTools: List[SystemToolDetail]
    systemPromptSections: List[SystemPromptSectionDetail]
    agents: List[Agent]
    slashCommands: SlashCommandInfo
    skills: SkillInfo
    autoCompactThreshold: float
    isAutoCompactEnabled: bool


# Fixed token overhead added by the API when tools are present.
TOOL_TOKEN_COUNT_OVERHEAD: Any = 500  # type: ignore


async def countTokensWithFallback(messages, tools):
    try:
        result = countMessagesTokensWithAPI(messages, tools)
        if result != None:
            return result
        logForDebugging(
        "countTokensWithFallback: API returned None, trying haiku fallback (${len(tools)} tools)",
        )
    except Exception as err:
        logForDebugging("countTokensWithFallback: API failed: ${errorMessage(err)}")
        logError(err)
    try:
        fallbackResult = countTokensViaHaikuFallback(messages, tools)
        if fallbackResult == None:
            logForDebugging(
            "countTokensWithFallback: haiku fallback also returned None (${len(tools)} tools)",
            )
        return fallbackResult
    except Exception as err:
        logForDebugging(
        "countTokensWithFallback: haiku fallback failed: ${errorMessage(err)}",
        )
        logError(err)
        return None


async def countToolDefinitionTokens(tools, getToolPermissionContext=None):
    total_tokens = 0
    tool_names: list[str] = []

    for tool in tools or []:
        tool_payload = await _serialize_tool_definition(tool)
        tool_names.append(str(tool_payload.get('name') or 'unknown'))
        total_tokens += roughTokenCountEstimation(jsonStringify(tool_payload))

    if total_tokens == 0:
        joined_names = ', '.join(tool_names)
        suffix = '...' if len(joined_names) > 100 else ''
        preview = joined_names[:100]
        logForDebugging(
            f'countToolDefinitionTokens returned 0 for {len(tool_names)} tools: {preview}{suffix}'
        )

    return total_tokens


async def _serialize_tool_definition(tool: Any) -> dict[str, Any]:
    name = _tool_attr(tool, 'name', 'TOOL_NAME') or 'unknown'
    input_schema = _tool_attr(tool, 'input_schema', 'INPUT_SCHEMA') or {}
    output_schema = _tool_attr(tool, 'output_schema', 'OUTPUT_SCHEMA') or {}
    prompt_value = await _resolve_tool_text(tool, 'prompt')
    description_value = await _resolve_tool_text(tool, 'description')

    return {
        'name': name,
        'description': description_value,
        'input_schema': input_schema,
        'output_schema': output_schema,
        'prompt': prompt_value,
        'aliases': _tool_aliases(tool),
    }


def _tool_attr(tool: Any, *names: str) -> Any:
    for name in names:
        if isinstance(tool, dict) and name in tool:
            return tool.get(name)
        if hasattr(tool, name):
            return getattr(tool, name)
    return None


async def _resolve_tool_text(tool: Any, attr_name: str) -> str:
    value = _tool_attr(tool, attr_name, attr_name.upper())
    if value is None:
        return ''
    try:
        if callable(value):
            resolved = value()
            if hasattr(resolved, '__await__'):
                resolved = await resolved
            return resolved if isinstance(resolved, str) else str(resolved)
        return value if isinstance(value, str) else str(value)
    except Exception as error:
        logError(error)
        return ''


def _tool_aliases(tool: Any) -> list[str]:
    aliases = _tool_attr(tool, 'aliases', 'ALIASES')
    if not isinstance(aliases, list):
        return []
    return [alias for alias in aliases if isinstance(alias, str)]


def extractSectionName(content):
    return content


async def countSystemTokens(effectiveSystemPrompt):
    return {
        'systemPromptTokens': 0,
        'systemPromptSections': [],
    }


async def countMemoryFileTokens():
    return {
        'memoryFileDetails': [],
        'vivianMdTokens': 0,
    }


async def countBuiltInToolTokens(tools, getToolPermissionContext=None):
    result = None
    _val = tools
    _count = len(_val) if hasattr(_val, "__len__") else 0
    return _count


def findSkillTool(tools):
    return findToolByName(tools, SKILL_TOOL_NAME)


async def countSlashCommandTokens(tools, getToolPermissionContext=None):
    result = None
    _val = tools
    _count = len(_val) if hasattr(_val, "__len__") else 0
    return _count


async def countSkillTokens(tools, getToolPermissionContext=None):
    result = None
    _val = tools
    _count = len(_val) if hasattr(_val, "__len__") else 0
    return _count


async def countMcpToolTokens(tools, getToolPermissionContext=None):
    result = None
    _val = tools
    _count = len(_val) if hasattr(_val, "__len__") else 0
    return _count


async def countCustomAgentTokens(agentDefinitions):
    return {
        'agentTokens': 0,
        'agentDetails': [],
    }


def processAssistantMessage(msg, breakdown):
    # Process each content block individually
    for block in msg.message.content:
        blockStr = jsonStringify(block)
        blockTokens = roughTokenCountEstimation(blockStr)
        if 'type' in block and block.type == 'tool_use':
            breakdown.toolCallTokens += blockTokens
            toolName = ('name' in block.name if block else None) or 'unknown'
            breakdown.toolCallsByType.set(
            toolName,
            (breakdown.toolCallsByType.get(toolName) or 0) + blockTokens,
            )
        else:
            # Text blocks or other non-tool content
            breakdown.assistantMessageTokens += blockTokens


def processUserMessage(msg, breakdown, toolUseIdToName):
    return msg


def processAttachment(msg, breakdown):
    contentStr = jsonStringify(msg.attachment)
    tokens = roughTokenCountEstimation(contentStr)
    breakdown.attachmentTokens += tokens
    attachType = msg.attachment.type or 'unknown'
    breakdown.attachmentsByType.set(
    attachType,
    (breakdown.attachmentsByType.get(attachType) or 0) + tokens,
    )


async def approximateMessageTokens(messages):
    result = None
    _input = messages
    _output = _input if _input is not None else {}
    return _output


async def analyzeContextUsage(messages, model, getToolPermissionContext=None, _options____mainThreadAgentDefinition__AgentDefinition______Original_messages_before_microcompact__used_to_extract_API_usage____originalMessages__Message___=None):
    result = None
    _input = messages
    _output = _input if _input is not None else {}
    return _output

