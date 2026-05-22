"""System init message builder — mirrors src/utils/messages/systemInit.ts"""
from __future__ import annotations

import os
import uuid as _uuid_mod
from typing import Any, Dict, List, Optional

# Tool name compatibility: the wire name was renamed Task -> Agent but SDK
# consumers may still expect the legacy name.
AGENT_TOOL_NAME = "Agent"
LEGACY_AGENT_TOOL_NAME = "Task"

CommandLike = Dict[str, Any]
SystemInitInputs = Dict[str, Any]


def sdk_compat_tool_name(name: str) -> str:
    """Return the legacy SDK tool name when the internal name is 'Agent'."""
    return LEGACY_AGENT_TOOL_NAME if name == AGENT_TOOL_NAME else name


# camelCase alias
sdkCompatToolName = sdk_compat_tool_name


def build_system_init_message(inputs: SystemInitInputs) -> Dict[str, Any]:
    """Build the ``system/init`` SDK message carrying session metadata.

    Mirrors buildSystemInitMessage() from systemInit.ts — called on the
    first query turn to tell remote clients which tools, commands, model,
    etc. are available.
    """
    tools = [sdk_compat_tool_name(t["name"]) for t in inputs.get("tools", [])]
    mcp_servers = [
        {"name": c["name"], "status": c.get("type", "connected")}
        for c in inputs.get("mcpClients", [])
    ]
    slash_commands = [
        c["name"]
        for c in inputs.get("commands", [])
        if c.get("userInvocable", True) is not False
    ]
    skills = [
        s["name"]
        for s in inputs.get("skills", [])
        if s.get("userInvocable", True) is not False
    ]
    agents = [a["agentType"] for a in inputs.get("agents", [])]
    plugins = [
        {"name": p["name"], "path": p["path"], "source": p["source"]}
        for p in inputs.get("plugins", [])
    ]

    return {
        "type": "system",
        "subtype": "init",
        "cwd": os.getcwd(),
        "session_id": None,  # populated by caller if needed
        "tools": tools,
        "mcp_servers": mcp_servers,
        "model": inputs.get("model", ""),
        "permissionMode": inputs.get("permissionMode", "default"),
        "slash_commands": slash_commands,
        "apiKeySource": inputs.get("apiKeySource", "env"),
        "betas": inputs.get("betas", []),
        "vivian_code_version": inputs.get("version", "unknown"),
        "output_style": inputs.get("outputStyle", "default"),
        "agents": agents,
        "skills": skills,
        "plugins": plugins,
        "uuid": str(_uuid_mod.uuid4()),
        "fast_mode_state": inputs.get("fastMode"),
    }


# camelCase alias
buildSystemInitMessage = build_system_init_message

