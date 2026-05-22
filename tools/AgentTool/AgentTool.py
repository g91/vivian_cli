"""AgentTool — mirrors src/tools/AgentTool/AgentTool.tsx."""
from __future__ import annotations

import uuid
from typing import Any, Dict

from .constants import AGENT_TOOL_NAME
from .loadAgentsDir import loadAgentsDir
from .prompt import getPrompt
from .runAgent import runAgent


TOOL_NAME = AGENT_TOOL_NAME

INPUT_SCHEMA = {
    "type": "object",
    "required": ["prompt"],
    "properties": {
        "prompt": {
            "type": "string",
            "description": "The task for the agent to perform",
        },
        "subagent_type": {
            "type": "string",
            "description": "The type of agent to spawn (e.g. Explore, Plan, general-purpose)",
        },
        "tools": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Specific tools to make available to the agent (overrides defaults)",
        },
        "disallowed_tools": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Tools to exclude from the agent's available tools",
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "output": {"type": "string", "description": "The agent's final output"},
        "agent_id": {"type": "string", "description": "The spawned agent's ID"},
        "subagent_type": {"type": "string", "description": "The type of agent used"},
    },
}


async def description() -> str:
    return "Launches a new agent to handle delegated tasks autonomously."


async def prompt(cwd: str = ".") -> str:
    agents = loadAgentsDir(cwd)
    agent_dicts = [
        {
            "agentType": a.agentType,
            "whenToUse": a.whenToUse,
            "tools": a.tools,
            "disallowedTools": a.disallowedTools,
        }
        for a in agents
    ]
    return await getPrompt(agent_dicts)


def userFacingName() -> str:
    return ""


def getToolUseSummary(input_data: Dict[str, Any]) -> str:
    return input_data.get("subagent_type", "agent")


def getActivityDescription(input_data: Dict[str, Any]) -> str:
    return f"Spawning {getToolUseSummary(input_data)} agent"


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    cwd = _context_get(context, "cwd") or "."
    agents = loadAgentsDir(cwd)
    requested_type = input_data.get("subagent_type") or "general-purpose"

    selected = None
    for agent in agents:
        if agent.agentType == requested_type:
            selected = {
                "agentType": agent.agentType,
                "whenToUse": agent.whenToUse,
                "tools": input_data.get("tools") if input_data.get("tools") is not None else list(agent.tools or []),
                "disallowedTools": input_data.get("disallowed_tools") if input_data.get("disallowed_tools") is not None else list(agent.disallowedTools or []),
                "systemPrompt": getattr(agent, "systemPrompt", None),
            }
            break

    if selected is None:
        selected = {
            "agentType": requested_type,
            "whenToUse": "General-purpose agent",
            "tools": input_data.get("tools") or [],
            "disallowedTools": input_data.get("disallowed_tools") or [],
            "systemPrompt": input_data.get("system_prompt"),
        }

    output = await runAgent(selected, input_data["prompt"])
    return {
        "output": output,
        "agent_id": str(uuid.uuid4()),
        "subagent_type": selected["agentType"],
    }


def _context_get(context: Any, key: str):
    if isinstance(context, dict):
        return context.get(key)
    return getattr(context, key, None)