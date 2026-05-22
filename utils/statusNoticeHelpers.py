"""
Port of src/utils/statusNoticeHelpers.ts
"""
from __future__ import annotations

from typing import Any

from ..services.tokenEstimation import roughTokenCountEstimation


AGENT_DESCRIPTIONS_THRESHOLD: Any = 15_000


def getAgentDescriptionsTotalTokens(agentDefinitions=None):
    """Calculate cumulative token estimate for agent descriptions"""
    if not agentDefinitions:
        return 0

    active_agents = getattr(agentDefinitions, "activeAgents", None)
    if active_agents is None and isinstance(agentDefinitions, dict):
        active_agents = agentDefinitions.get("activeAgents", [])
    if active_agents is None:
        active_agents = []

    total = 0
    for agent in active_agents:
        if isinstance(agent, dict):
            source = agent.get("source")
            agent_type = agent.get("agentType", "")
            when_to_use = agent.get("whenToUse", "")
        else:
            source = getattr(agent, "source", None)
            agent_type = getattr(agent, "agentType", "")
            when_to_use = getattr(agent, "whenToUse", "")
        if source == "built-in":
            continue
        total += roughTokenCountEstimation(f"{agent_type}: {when_to_use}")
    return total


get_agent_descriptions_total_tokens = getAgentDescriptionsTotalTokens

