"""AgentTool utilities — mirrors src/tools/AgentTool/agentToolUtils.ts"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


def buildAgentInput(
    prompt: str,
    subagentType: str,
    tools: Optional[List[str]] = None,
    disallowedTools: Optional[List[str]] = None,
    systemPrompt: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the input dict for spawning an agent."""
    inp: Dict[str, Any] = {
        "prompt": prompt,
        "subagent_type": subagentType,
    }
    if tools is not None:
        inp["tools"] = tools
    if disallowedTools is not None:
        inp["disallowed_tools"] = disallowedTools
    if systemPrompt is not None:
        inp["system_prompt"] = systemPrompt
    return inp


def extractAgentResult(result: Any) -> str:
    """Extract the text result from an agent invocation result."""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return result.get("output", str(result))
    return str(result)


def formatAgentError(error: Exception) -> str:
    """Format an agent error for display."""
    return f"Agent error: {type(error).__name__}: {error}"
