"""Agent runner — mirrors src/tools/AgentTool/runAgent.ts."""
from __future__ import annotations

import os
from typing import Any, Callable, Dict, Optional

from ...api.client import VivianClient
from ...tools.registry import ToolRegistry
from .builtInAgents import getBuiltInAgentDefinitions
from .loadAgentsDir import AgentDefinition, loadAgentsDir


async def runAgent(
    agentDefinition: Dict[str, Any],
    prompt: str,
    onProgress: Optional[Callable[[str], None]] = None,
) -> str:
    """Run an agent with the given definition and prompt."""
    resolved_agent = _normalize_agent_definition(agentDefinition)
    if onProgress:
        onProgress(f"Starting {resolved_agent.get('agentType', 'general-purpose')} agent...")

    registry = _build_agent_registry(resolved_agent)
    client = VivianClient(
        api_key=os.environ.get("VIVIAN_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"),
        admin_jwt=os.environ.get("VIVIAN_ADMIN_JWT"),
        base_url=os.environ.get("VIVIAN_API_BASE_URL") or os.environ.get("VIVIAN_INTERNAL_URL") or "http://localhost:5000",
        default_model=os.environ.get("VIVIAN_DEFAULT_MODEL", "qwen3.6"),
    )

    append_prompt = resolved_agent.get("systemPrompt")
    from ...query_engine import QueryEngine  # deferred to break circular import
    engine = QueryEngine(
        client,
        tool_registry=registry,
        cwd=os.getcwd(),
        append_system_prompt=append_prompt,
        model=os.environ.get("VIVIAN_DEFAULT_MODEL", "qwen3.6"),
    )

    output_parts: list[str] = []
    try:
        async for event in engine.submit_message(prompt):
            progress_text = _extract_progress_text(event)
            if progress_text and onProgress:
                onProgress(progress_text)

            assistant_text = _extract_assistant_text(event)
            if assistant_text:
                output_parts.append(assistant_text)
    finally:
        await client.close()

    result = "".join(output_parts).strip()
    return result or "Execution completed."


def _normalize_agent_definition(agent_definition: Dict[str, Any] | AgentDefinition) -> Dict[str, Any]:
    if isinstance(agent_definition, dict):
        normalized = dict(agent_definition)
    else:
        normalized = {
            "agentType": agent_definition.agentType,
            "whenToUse": agent_definition.whenToUse,
            "tools": list(getattr(agent_definition, "tools", []) or []),
            "disallowedTools": list(getattr(agent_definition, "disallowedTools", []) or []),
            "systemPrompt": getattr(agent_definition, "systemPrompt", None),
        }

    if normalized.get("agentType"):
        return normalized

    agent_type = normalized.get("subagent_type") or normalized.get("agent_type") or "general-purpose"
    for built_in in getBuiltInAgentDefinitions():
        if built_in.get("agentType") == agent_type:
            merged = dict(built_in)
            merged.update(normalized)
            return merged
    return {
        "agentType": agent_type,
        "whenToUse": "General-purpose agent",
        "tools": normalized.get("tools") or [],
        "disallowedTools": normalized.get("disallowedTools") or [],
        "systemPrompt": normalized.get("systemPrompt"),
    }


def _build_agent_registry(agent_definition: Dict[str, Any]) -> ToolRegistry:
    from ...tools.all_tools import register_all_tools

    base_registry = ToolRegistry()
    register_all_tools(base_registry)

    allowed_tools = set(agent_definition.get("tools") or [])
    disallowed_tools = set(agent_definition.get("disallowedTools") or [])

    registry = ToolRegistry()
    for tool in base_registry.get_enabled_tools():
        tool_name = getattr(tool, "name", None)
        if not tool_name:
            continue
        if allowed_tools and tool_name not in allowed_tools:
            continue
        if tool_name in disallowed_tools:
            continue
        registry.register(tool, base_registry.get_handler(tool_name))
    return registry


def _extract_progress_text(event: Any) -> Optional[str]:
    if isinstance(event, dict):
        if event.get("type") == "tool_call_start":
            return f"Running {event.get('name')}..."
        if event.get("type") == "tool_call_args":
            return f"Calling {event.get('name')}"
    role = getattr(event, "role", None)
    if role == "system":
        return getattr(event, "content", None)
    return None


def _extract_assistant_text(event: Any) -> str:
    role = getattr(event, "role", None)
    if role == "assistant":
        return str(getattr(event, "content", "") or "")

    choices = getattr(event, "choices", None)
    if isinstance(choices, list):
        fragments: list[str] = []
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            delta = choice.get("delta") or {}
            if isinstance(delta, dict) and isinstance(delta.get("content"), str):
                fragments.append(delta["content"])
        return "".join(fragments)
    return ""
