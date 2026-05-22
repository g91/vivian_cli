"""Agent ID formatting — mirrors src/utils/agentId.ts"""
from __future__ import annotations

import time
from typing import Optional


def format_agent_id(agent_name: str, team_name: str) -> str:
    """Format an agent ID as ``agentName@teamName``."""
    return f"{agent_name}@{team_name}"


def parse_agent_id(agent_id: str) -> Optional[dict[str, str]]:
    """Parse ``agentName@teamName`` into its components. Returns None if invalid."""
    at = agent_id.find("@")
    if at == -1:
        return None
    return {"agent_name": agent_id[:at], "team_name": agent_id[at + 1:]}


def generate_request_id(request_type: str, agent_id: str) -> str:
    """Format a request ID as ``{requestType}-{timestamp}@{agentId}``."""
    timestamp = int(time.time() * 1000)
    return f"{request_type}-{timestamp}@{agent_id}"


def parse_request_id(request_id: str) -> Optional[dict]:
    """Parse a request ID. Returns None if it doesn't match the expected format."""
    at = request_id.find("@")
    if at == -1:
        return None
    prefix = request_id[:at]
    agent_id = request_id[at + 1:]
    dash = prefix.rfind("-")
    if dash == -1:
        return None
    request_type = prefix[:dash]
    try:
        timestamp = int(prefix[dash + 1:])
    except ValueError:
        return None
    return {"request_type": request_type, "timestamp": timestamp, "agent_id": agent_id}
