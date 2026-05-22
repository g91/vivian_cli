"""Load agents from .vivian/agents/ directory — mirrors src/tools/AgentTool/loadAgentsDir.ts"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .builtInAgents import getBuiltInAgentDefinitions


@dataclass
class AgentDefinition:
    agentType: str
    whenToUse: str
    tools: List[str] = field(default_factory=list)
    disallowedTools: List[str] = field(default_factory=list)
    systemPrompt: Optional[str] = None
    isCustom: bool = False


@dataclass
class CustomAgentDefinition(AgentDefinition):
    filePath: Optional[str] = None
    isCustom: bool = True


def isCustomAgent(agent: AgentDefinition) -> bool:
    return agent.isCustom


def loadAgentsDir(cwd: str) -> List[AgentDefinition]:
    """Load all agent definitions (built-in + custom from .vivian/agents/)."""
    agents: List[AgentDefinition] = []

    # Built-in agents first
    for d in getBuiltInAgentDefinitions():
        agents.append(AgentDefinition(**d))

    # Load custom agents from .vivian/agents/
    agents_dir = Path(cwd) / ".vivian" / "agents"
    if agents_dir.exists() and agents_dir.is_dir():
        for agent_file in sorted(agents_dir.glob("*.json")):
            try:
                data = json.loads(agent_file.read_text(encoding="utf-8"))
                agents.append(CustomAgentDefinition(
                    agentType=data.get("agentType", agent_file.stem),
                    whenToUse=data.get("whenToUse", ""),
                    tools=data.get("tools", []),
                    disallowedTools=data.get("disallowedTools", []),
                    systemPrompt=data.get("systemPrompt"),
                    filePath=str(agent_file),
                ))
            except (json.JSONDecodeError, KeyError, OSError):
                continue

    return agents
