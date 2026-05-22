"""Port of src/utils/model/agent.ts"""
from __future__ import annotations

import os
from typing import List, Optional

from .aliases import MODEL_ALIASES, ModelAlias

AGENT_MODEL_OPTIONS = list(MODEL_ALIASES) + ['inherit']
AgentModelAlias = str

class AgentModelOption:
    def __init__(self, value: str, label: str, description: str):
        self.value = value
        self.label = label
        self.description = description

def getDefaultSubagentModel() -> str:
    return 'inherit'

def _get_bedrock_region_prefix(model: str) -> Optional[str]:
    try:
        from .bedrock import getBedrockRegionPrefix
        return getBedrockRegionPrefix(model)
    except Exception:
        return None

def _apply_bedrock_region_prefix(model: str, prefix: str) -> str:
    try:
        from .bedrock import applyBedrockRegionPrefix
        return applyBedrockRegionPrefix(model, prefix)
    except Exception:
        return model

def _alias_matches_parent_tier(alias: str, parent_model: str) -> bool:
    from .model import getCanonicalName
    canonical = getCanonicalName(parent_model)
    a = alias.lower()
    if a == 'opus':
        return 'opus' in canonical
    if a == 'sonnet':
        return 'sonnet' in canonical
    if a == 'haiku':
        return 'haiku' in canonical
    return False

def getAgentModel(
    agent_model: Optional[str],
    parent_model: str,
    tool_specified_model: Optional[ModelAlias] = None,
    permission_mode: Optional[str] = None,
) -> str:
    env_override = os.environ.get('vivian_CODE_SUBAGENT_MODEL')
    if env_override:
        from .model import parseUserSpecifiedModel
        return parseUserSpecifiedModel(env_override)

    from .providers import getAPIProvider
    from .model import parseUserSpecifiedModel, getRuntimeMainLoopModel
    parent_region_prefix = _get_bedrock_region_prefix(parent_model)

    def apply_parent_region_prefix(resolved: str, original_spec: str) -> str:
        if parent_region_prefix and getAPIProvider() == 'bedrock':
            if _get_bedrock_region_prefix(original_spec):
                return resolved
            return _apply_bedrock_region_prefix(resolved, parent_region_prefix)
        return resolved

    if tool_specified_model:
        if _alias_matches_parent_tier(tool_specified_model, parent_model):
            return parent_model
        model = parseUserSpecifiedModel(tool_specified_model)
        return apply_parent_region_prefix(model, tool_specified_model)

    agent_model_with_exp = agent_model if agent_model is not None else getDefaultSubagentModel()

    if agent_model_with_exp == 'inherit':
        return getRuntimeMainLoopModel({
            'permissionMode': permission_mode or 'default',
            'mainLoopModel': parent_model,
            'exceeds200kTokens': False,
        })

    if _alias_matches_parent_tier(agent_model_with_exp, parent_model):
        return parent_model
    model = parseUserSpecifiedModel(agent_model_with_exp)
    return apply_parent_region_prefix(model, agent_model_with_exp)

def getAgentModelDisplay(model: Optional[str]) -> str:
    if not model:
        return 'Inherit from parent (default)'
    if model == 'inherit':
        return 'Inherit from parent'
    return model.capitalize()

def getAgentModelOptions() -> List[AgentModelOption]:
    return [
        AgentModelOption('sonnet', 'Sonnet', 'Balanced performance - best for most agents'),
        AgentModelOption('opus', 'Opus', 'Most capable for complex reasoning tasks'),
        AgentModelOption('haiku', 'Haiku', 'Fast and efficient for simple tasks'),
        AgentModelOption('inherit', 'Inherit from parent', 'Use same model as parent thread'),
    ]
