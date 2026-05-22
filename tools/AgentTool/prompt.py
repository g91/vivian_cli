"""AgentTool prompt — mirrors src/tools/AgentTool/prompt.ts"""
from __future__ import annotations
import os
from typing import Any, Optional, List
from .constants import AGENT_TOOL_NAME


def getToolsDescription(agent: dict) -> str:
    tools = agent.get("tools") or []
    disallowedTools = agent.get("disallowedTools") or []
    hasAllowlist = len(tools) > 0
    hasDenylist = len(disallowedTools) > 0
    if hasAllowlist and hasDenylist:
        denySet = set(disallowedTools)
        effectiveTools = [t for t in tools if t not in denySet]
        return "None" if not effectiveTools else ", ".join(effectiveTools)
    elif hasAllowlist:
        return ", ".join(tools)
    elif hasDenylist:
        return f"All tools except {', '.join(disallowedTools)}"
    return "All tools"


def formatAgentLine(agent: dict) -> str:
    """Format one agent line for the agent_listing_delta attachment message."""
    toolsDescription = getToolsDescription(agent)
    return f"- {agent.get('agentType')}: {agent.get('whenToUse')} (Tools: {toolsDescription})"


def shouldInjectAgentListInMessages() -> bool:
    """Whether the agent list should be injected as an attachment message."""
    val = os.environ.get("vivian_CODE_AGENT_LIST_IN_MESSAGES", "")
    if val.lower() in ("1", "true", "yes"):
        return True
    if val.lower() in ("0", "false", "no"):
        return False
    return False


async def getPrompt(
    agentDefinitions: List[dict],
    isCoordinator: bool = False,
    allowedAgentTypes: Optional[List[str]] = None,
) -> str:
    effectiveAgents = (
        [a for a in agentDefinitions if a.get("agentType") in allowedAgentTypes]
        if allowedAgentTypes
        else agentDefinitions
    )

    agent_lines = "\n".join(formatAgentLine(a) for a in effectiveAgents)

    return f"""Launches a new agent subagent to handle delegated tasks autonomously.

## Available agent types
{agent_lines}

## When to use {AGENT_TOOL_NAME}
- Complex multi-step tasks that benefit from delegation
- Open-ended search tasks requiring multiple rounds of exploration
- Tasks where you want to parallelize independent subtasks

## Usage
- subagent_type: The type of agent to launch (from the list above)
- prompt: The task description for the agent
- The agent runs autonomously and returns results when complete
"""
