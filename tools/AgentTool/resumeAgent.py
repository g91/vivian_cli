"""Agent resume logic — mirrors src/tools/AgentTool/resumeAgent.ts"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


def canResumeAgent(agentState: Dict[str, Any]) -> bool:
    """Check if an agent can be resumed."""
    return agentState.get("status") in ("paused", "waiting")


def buildResumeInput(agentId: str, message: str) -> Dict[str, Any]:
    """Build the input for resuming an agent with a message."""
    return {
        "agent_id": agentId,
        "message": message,
        "action": "resume",
    }
