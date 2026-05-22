"""agents command — text-mode listing for configured agents.

The TypeScript slash command opens an interactive menu. The Python CLI currently
uses a non-interactive fallback, so this command should expose the live agent
definitions that the session knows about rather than placeholder text.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import TYPE_CHECKING, Any, Iterable

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    action = args.strip().lower()
    if action and action != "list":
        return TextResult("Usage: /agents")
    return TextResult(_list_agents(context))


def _list_agents(context: CommandContext) -> str:
    agent_definitions = _get_agent_definitions(context)
    all_agents = _normalize_agents(_agent_defs_get(agent_definitions, "allAgents") or [])
    active_agents = _normalize_agents(_agent_defs_get(agent_definitions, "activeAgents") or all_agents)

    if not all_agents:
        return "No agents found."

    active_names = {
        _agent_field(agent, "agentType")
        for agent in active_agents
        if _agent_field(agent, "agentType")
    }
    total_active = sum(
        1 for agent in all_agents if _agent_field(agent, "agentType") in active_names
    )

    built_in = []
    custom = []
    other = []
    for agent in all_agents:
        bucket = _classify_agent(agent)
        if bucket == "built-in":
            built_in.append(agent)
        elif bucket == "custom":
            custom.append(agent)
        else:
            other.append(agent)

    lines = [f"{total_active} active agents", ""]
    for label, group in (("Built-in", built_in), ("Custom", custom), ("Other", other)):
        if not group:
            continue
        lines.append(f"{label}:")
        for agent in sorted(group, key=lambda item: (_agent_field(item, "agentType") or "").lower()):
            prefix = "*" if _agent_field(agent, "agentType") in active_names else "-"
            lines.append(f"  {prefix} {_format_agent(agent)}")
        lines.append("")

    return "\n".join(lines).rstrip()


def _get_agent_definitions(context: Any) -> Any:
    state_store = getattr(context, "state_store", None)
    if state_store is not None and hasattr(state_store, "get_state"):
        try:
            state = state_store.get_state() or {}
            agent_definitions = state.get("agentDefinitions")
            if agent_definitions:
                return agent_definitions
        except Exception:
            pass

    app_state = getattr(context, "app_state", None)
    if app_state is not None:
        if isinstance(app_state, dict):
            agent_definitions = app_state.get("agentDefinitions")
        else:
            agent_definitions = getattr(app_state, "agentDefinitions", None)
        if agent_definitions:
            return agent_definitions

    context_dict = getattr(context, "__dict__", {}) if not isinstance(context, dict) else context
    engine = (
        context_dict.get("query_engine")
        or context_dict.get("engine")
        or context_dict.get("_engine")
    )
    if engine is not None:
        nested_state_store = getattr(engine, "state_store", None)
        if nested_state_store is not None and hasattr(nested_state_store, "get_state"):
            try:
                state = nested_state_store.get_state() or {}
                agent_definitions = state.get("agentDefinitions")
                if agent_definitions:
                    return agent_definitions
            except Exception:
                pass

    try:
        from ...tools.AgentTool.loadAgentsDir import loadAgentsDir

        cwd = getattr(context, "cwd", None) or "."
        loaded_agents = loadAgentsDir(cwd)
        return {"allAgents": loaded_agents, "activeAgents": loaded_agents}
    except Exception:
        return {"allAgents": [], "activeAgents": []}


def _agent_defs_get(agent_definitions: Any, key: str) -> Any:
    if isinstance(agent_definitions, dict):
        return agent_definitions.get(key)
    return getattr(agent_definitions, key, None)


def _normalize_agents(agents: Iterable[Any]) -> list[dict[str, Any]]:
    normalized = []
    for agent in agents or []:
        if isinstance(agent, dict):
            normalized.append(dict(agent))
        elif is_dataclass(agent):
            normalized.append(asdict(agent))
        else:
            normalized.append(getattr(agent, "__dict__", {}) or {})
    return normalized


def _agent_field(agent: dict[str, Any], key: str) -> Any:
    return agent.get(key)


def _classify_agent(agent: dict[str, Any]) -> str:
    source = (_agent_field(agent, "source") or "").lower()
    if source in {"built-in", "builtin"}:
        return "built-in"
    if source in {"custom", "user", "project"}:
        return "custom"
    if agent.get("isCustom") or agent.get("filePath"):
        return "custom"
    if source:
        return "other"
    return "built-in"


def _format_agent(agent: dict[str, Any]) -> str:
    parts = [str(_agent_field(agent, "agentType") or "unknown")]
    model = _agent_field(agent, "model")
    memory = _agent_field(agent, "memory")
    when_to_use = _agent_field(agent, "whenToUse")

    if model:
        parts.append(str(model))
    if memory:
        parts.append(f"{memory} memory")

    formatted = " · ".join(parts)
    if when_to_use:
        formatted = f"{formatted} - {str(when_to_use)}"
    return formatted


showAgents = _list_agents
show_agents = _list_agents
