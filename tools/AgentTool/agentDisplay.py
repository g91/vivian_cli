"""AgentTool display utilities — mirrors src/tools/AgentTool/agentDisplay.ts"""
from __future__ import annotations
from typing import Any, Optional


def formatAgentStatus(agentId: str, status: str, message: Optional[str] = None) -> str:
    """Format an agent status line for display."""
    parts = [f"[{agentId}] {status}"]
    if message:
        parts.append(f": {message}")
    return "".join(parts)


def formatAgentOutput(agentId: str, output: Any) -> str:
    """Format agent output for display in the UI."""
    if isinstance(output, str):
        return f"[{agentId}]\n{output}"
    return f"[{agentId}]\n{str(output)}"


def renderAgentToolUseMessage(agentId: str, input_data: dict) -> str:
    """Render a tool use message for an agent invocation."""
    return f"Spawning agent: {agentId}"


def renderAgentResultMessage(agentId: str, result: Any) -> str:
    """Render a result message from a completed agent."""
    return f"Agent {agentId} completed."
