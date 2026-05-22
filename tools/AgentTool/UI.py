"""AgentTool UI rendering — mirrors src/tools/AgentTool/UI.tsx"""
from __future__ import annotations
from typing import Any, Dict, Optional


def renderToolUseMessage(input_data: Dict[str, Any]) -> Optional[str]:
    description = input_data.get("description")
    prompt = input_data.get("prompt")
    if description and prompt:
        return str(description)

    subagent_type = input_data.get("subagent_type", "agent")
    prompt_text = str(prompt or "")
    if not prompt_text:
        return None
    return f"Spawning {subagent_type} agent: {prompt_text[:80]}"


def renderToolResultMessage(result: Dict[str, Any]) -> str:
    output = result.get("output", "")
    return output[:2000] if output else "(no output)"


def renderToolUseErrorMessage(error: str) -> str:
    return f"Agent error: {error}"
