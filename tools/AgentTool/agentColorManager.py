"""AgentTool color manager — mirrors src/tools/AgentTool/agentColorManager.ts"""
from __future__ import annotations
from typing import Dict, Optional

# ANSI color codes for agent display
_AGENT_COLORS = [
    "\033[36m",   # cyan
    "\033[33m",   # yellow
    "\033[35m",   # magenta
    "\033[32m",   # green
    "\033[34m",   # blue
    "\033[31m",   # red
]
_RESET = "\033[0m"

_agent_color_map: Dict[str, str] = {}
_color_index = 0


def getAgentColor(agentId: str) -> str:
    """Get or assign a consistent color for an agent ID."""
    global _color_index
    if agentId not in _agent_color_map:
        _agent_color_map[agentId] = _AGENT_COLORS[_color_index % len(_AGENT_COLORS)]
        _color_index += 1
    return _agent_color_map[agentId]


def colorizeAgentOutput(agentId: str, text: str) -> str:
    """Wrap text in the agent's assigned color."""
    color = getAgentColor(agentId)
    return f"{color}{text}{_RESET}"


def resetAgentColors() -> None:
    """Reset all agent color assignments (e.g., for testing)."""
    global _color_index
    _agent_color_map.clear()
    _color_index = 0
