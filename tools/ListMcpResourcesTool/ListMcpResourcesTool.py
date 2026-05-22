"""ListMcpResourcesTool — mirrors src/tools/ListMcpResourcesTool/ListMcpResourcesTool.tsx"""
from __future__ import annotations

import inspect
from typing import Any, Dict

from ...utils.log import logMCPError

TOOL_NAME = "mcp__list_resources"

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "server": {"type": "string", "description": "Optional MCP server name to filter by"},
    },
}


async def description() -> str:
    return "List available MCP resources from connected servers."


async def prompt() -> str:
    return "Use this tool to list available resources from connected MCP servers."


def _client_value(client: Any, key: str, default: Any = None) -> Any:
    if isinstance(client, dict):
        return client.get(key, default)
    return getattr(client, key, default)


def _capability_value(capabilities: Any, key: str, default: Any = None) -> Any:
    if isinstance(capabilities, dict):
        return capabilities.get(key, default)
    return getattr(capabilities, key, default)


def _get_mcp_clients(context: Any) -> list[Any]:
    if isinstance(context, dict):
        if isinstance(context.get("mcpClients"), list):
            return context["mcpClients"]
        options = context.get("options")
        if isinstance(options, dict) and isinstance(options.get("mcpClients"), list):
            return options["mcpClients"]
    return []


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _fetch_client_resources(client: Any) -> list[dict[str, Any]]:
    direct_resources = _client_value(client, "resources")
    if isinstance(direct_resources, list):
        return [item for item in direct_resources if isinstance(item, dict)]

    requester = _client_value(client, "client")
    request = getattr(requester, "request", None) if requester is not None else None
    if request is None:
        request = getattr(client, "request", None)
    if not callable(request):
        return []

    result = await _maybe_await(request({"method": "resources/list", "params": {}}))
    if isinstance(result, dict) and isinstance(result.get("resources"), list):
        return [item for item in result["resources"] if isinstance(item, dict)]
    return []


def _client_supports_resources(client: Any) -> bool:
    capabilities = _client_value(client, "capabilities") or {}
    if _capability_value(capabilities, "resources"):
        return True
    return _client_value(client, "resources") is not None


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    target_server = input_data.get("server")
    mcp_clients = _get_mcp_clients(context)

    clients_to_process = [
        client for client in mcp_clients
        if not target_server or _client_value(client, "name") == target_server
    ]

    if target_server and not clients_to_process:
        available = ", ".join(str(_client_value(client, "name", "")) for client in mcp_clients if _client_value(client, "name"))
        return {"error": f'Server "{target_server}" not found. Available servers: {available}'}

    resources: list[dict[str, Any]] = []
    for client in clients_to_process:
        if _client_value(client, "type") != "connected":
            continue
        if not _client_supports_resources(client):
            continue
        try:
            for resource in await _fetch_client_resources(client):
                resources.append(
                    {
                        "uri": resource.get("uri", ""),
                        "name": resource.get("name") or resource.get("uri", ""),
                        "mimeType": resource.get("mimeType"),
                        "description": resource.get("description"),
                        "server": _client_value(client, "name", ""),
                    }
                )
        except Exception as exc:
            logMCPError(str(_client_value(client, "name", "")), str(exc))
            continue

    return resources
