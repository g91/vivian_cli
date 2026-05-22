"""AgentTool package — mirrors src/tools/AgentTool/"""
from .constants import (
    AGENT_TOOL_NAME,
    LEGACY_AGENT_TOOL_NAME,
    VERIFICATION_AGENT_TYPE,
    ONE_SHOT_BUILTIN_AGENT_TYPES,
)
from .loadAgentsDir import AgentDefinition, CustomAgentDefinition, loadAgentsDir, isCustomAgent

__all__ = [
    "AGENT_TOOL_NAME",
    "LEGACY_AGENT_TOOL_NAME",
    "VERIFICATION_AGENT_TYPE",
    "ONE_SHOT_BUILTIN_AGENT_TYPES",
    "AgentDefinition",
    "CustomAgentDefinition",
    "loadAgentsDir",
    "isCustomAgent",
]
