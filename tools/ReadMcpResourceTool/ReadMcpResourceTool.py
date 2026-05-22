"""ReadMcpResourceTool — mirrors src/tools/ReadMcpResourceTool/ReadMcpResourceTool.tsx"""
from __future__ import annotations

import base64
import inspect
import time
from typing import Any, Dict

from ...utils.mcpOutputStorage import getBinaryBlobSavedMessage, persistBinaryContent

TOOL_NAME = "mcp__read_resource"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["server", "uri"],
    "properties": {
        "server": {"type": "string"},
        "uri": {"type": "string"},
    },
}


async def description() -> str:
    return "Read a resource from a connected MCP server."


async def prompt() -> str:
    return "Use this tool to read a resource exposed by a connected MCP server by URI."


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


async def _request_resource_read(client: Any, uri: str) -> dict[str, Any]:
    requester = _client_value(client, "client")
    request = getattr(requester, "request", None) if requester is not None else None
    if request is None:
        request = getattr(client, "request", None)
    if not callable(request):
        raise RuntimeError("MCP client does not support resource reads")
    result = await _maybe_await(request({"method": "resources/read", "params": {"uri": uri}}))
    if isinstance(result, dict):
        return result
    raise RuntimeError("Invalid MCP resource read response")


def _client_supports_resources(client: Any) -> bool:
    capabilities = _client_value(client, "capabilities") or {}
    if _capability_value(capabilities, "resources"):
        return True
    return _client_value(client, "resources") is not None


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    server_name = input_data.get("server")
    uri = input_data.get("uri")
    mcp_clients = _get_mcp_clients(context)

    client = next((item for item in mcp_clients if _client_value(item, "name") == server_name), None)
    if client is None:
        available = ", ".join(str(_client_value(item, "name", "")) for item in mcp_clients if _client_value(item, "name"))
        return {"error": f'Server "{server_name}" not found. Available servers: {available}'}
    if _client_value(client, "type") != "connected":
        return {"error": f'Server "{server_name}" is not connected'}

    if not _client_supports_resources(client):
        return {"error": f'Server "{server_name}" does not support resources'}

    try:
        result = await _request_resource_read(client, str(uri))
    except Exception as exc:
        return {"error": str(exc)}

    contents: list[dict[str, Any]] = []
    for index, content in enumerate(result.get("contents", []) if isinstance(result, dict) else []):
        if not isinstance(content, dict):
            continue
        if isinstance(content.get("text"), str):
            contents.append(
                {
                    "uri": content.get("uri", uri),
                    "mimeType": content.get("mimeType"),
                    "text": content.get("text"),
                }
            )
            continue
        blob = content.get("blob")
        if isinstance(blob, str):
            persist_id = f"mcp-resource-{int(time.time() * 1000)}-{index}"
            persisted = await persistBinaryContent(base64.b64decode(blob), content.get("mimeType"), persist_id)
            if isinstance(persisted, dict) and persisted.get("filepath"):
                contents.append(
                    {
                        "uri": content.get("uri", uri),
                        "mimeType": content.get("mimeType"),
                        "blobSavedTo": persisted["filepath"],
                        "text": getBinaryBlobSavedMessage(
                            persisted["filepath"],
                            content.get("mimeType"),
                            persisted.get("size", 0),
                            f"[Resource from {server_name} at {content.get('uri', uri)}] ",
                        ),
                    }
                )
                continue
            contents.append(
                {
                    "uri": content.get("uri", uri),
                    "mimeType": content.get("mimeType"),
                    "text": f"Binary content could not be saved to disk: {persisted.get('error', 'unknown error')}",
                }
            )
            continue
        contents.append({"uri": content.get("uri", uri), "mimeType": content.get("mimeType")})

    return {"contents": contents}
