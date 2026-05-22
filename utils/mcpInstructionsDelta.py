"""
Port of src/utils/mcpInstructionsDelta.ts
"""
from __future__ import annotations

from typing import Any, Dict
import os

from ..services.analytics.growthbook import getFeatureValue_CACHED_MAY_BE_STALE
from ..services.analytics.index import logEvent
from .envUtils import is_env_defined_falsy, is_env_truthy


McpInstructionsDelta = Dict[str, Any]
ClientSideInstruction = Dict[str, Any]


def isMcpInstructionsDeltaEnabled():
    """True → announce MCP server instructions via persisted delta attachments.
False → prompts.ts keeps its DANGEROUS_uncachedSystemPromptSection
(rebuilt every turn; cache-busts on late connect).

Env override for local testing: vivian_CODE_MCP_INSTR_DELTA=true/false
wins over both ant bypass and the GrowthBook gate."""
    if is_env_truthy(os.environ.get("vivian_CODE_MCP_INSTR_DELTA")):
        return True
    if is_env_defined_falsy(os.environ.get("vivian_CODE_MCP_INSTR_DELTA")):
        return False
    return os.environ.get("USER_TYPE") == "ant" or bool(
        getFeatureValue_CACHED_MAY_BE_STALE("tengu_basalt_3kr", False)
    )


def getMcpInstructionsDelta(mcpClients, messages, clientSideInstructions):
    """Diff the current set of connected MCP servers that have instructions
(server-authored via InitializeResult, or client-side synthesized)
against what's already been announced in this conversation. Null if
nothing changed.

Instructions are immutable for the life of a connection (set once at
handshake), so the scan diffs on server NAME, not on content."""
    announced: set[str] = set()
    attachment_count = 0
    mid_count = 0

    for msg in messages or []:
        if not isinstance(msg, dict) or msg.get("type") != "attachment":
            continue
        attachment_count += 1
        attachment = msg.get("attachment") or {}
        if attachment.get("type") != "mcp_instructions_delta":
            continue
        mid_count += 1
        for name in attachment.get("addedNames", []) or []:
            announced.add(str(name))
        for name in attachment.get("removedNames", []) or []:
            announced.discard(str(name))

    connected = [
        client for client in (mcpClients or [])
        if isinstance(client, dict) and client.get("type") == "connected"
    ]
    connected_names = {str(client.get("name", "")) for client in connected if client.get("name")}

    blocks: dict[str, str] = {}
    for client in connected:
        name = client.get("name")
        instructions = client.get("instructions")
        if name and instructions:
            blocks[str(name)] = f"## {name}\n{instructions}"

    for client_instruction in clientSideInstructions or []:
        if not isinstance(client_instruction, dict):
            continue
        server_name = client_instruction.get("serverName")
        block = client_instruction.get("block")
        if not server_name or not block or server_name not in connected_names:
            continue
        existing = blocks.get(server_name)
        blocks[server_name] = (
            f"{existing}\n\n{block}" if existing else f"## {server_name}\n{block}"
        )

    added: list[dict[str, str]] = []
    for name, block in blocks.items():
        if name not in announced:
            added.append({"name": name, "block": block})

    removed = sorted(name for name in announced if name not in connected_names)

    if not added and not removed:
        return None

    logEvent(
        "tengu_mcp_instructions_pool_change",
        {
            "addedCount": len(added),
            "removedCount": len(removed),
            "priorAnnouncedCount": len(announced),
            "clientSideCount": len(clientSideInstructions or []),
            "messagesLength": len(messages or []),
            "attachmentCount": attachment_count,
            "midCount": mid_count,
        },
    )

    added.sort(key=lambda item: item["name"])
    return {
        "addedNames": [item["name"] for item in added],
        "addedBlocks": [item["block"] for item in added],
        "removedNames": removed,
    }


is_mcp_instructions_delta_enabled = isMcpInstructionsDeltaEnabled
get_mcp_instructions_delta = getMcpInstructionsDelta

