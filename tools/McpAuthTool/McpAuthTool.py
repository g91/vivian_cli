"""McpAuthTool — mirrors src/tools/McpAuthTool/McpAuthTool.tsx"""
from __future__ import annotations
import inspect
from typing import Any, Dict

TOOL_NAME = "mcp__auth"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["server"],
    "properties": {
        "server": {"type": "string", "description": "MCP server name to authenticate with"},
        "token": {"type": "string", "description": "Authentication token"},
    },
}


async def description() -> str:
    return "Authenticate with an MCP server."


async def prompt() -> str:
    return "Use this tool to authenticate with an MCP server that requires credentials."


def _client_value(client: Any, key: str, default: Any = None) -> Any:
    if isinstance(client, dict):
        return client.get(key, default)
    return getattr(client, key, default)


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


def _target_object(client: Any) -> Any:
    return _client_value(client, "client") or client


async def _set_client_token(client: Any, token: str) -> bool:
    target = _target_object(client)
    for attr in ("authenticate", "set_auth_token", "setAuthToken", "set_token", "setToken"):
        fn = getattr(target, attr, None)
        if callable(fn):
            await _maybe_await(fn(token))
            return True
    if isinstance(target, dict):
        target["authToken"] = token
        return True
    if hasattr(target, "authToken"):
        setattr(target, "authToken", token)
        return True
    if hasattr(target, "token"):
        setattr(target, "token", token)
        return True
    return False


async def _reconnect_client(client: Any) -> None:
    target = _target_object(client)
    for attr in ("reconnect", "connect", "refresh", "restart"):
        fn = getattr(target, attr, None)
        if callable(fn):
            await _maybe_await(fn())
            return


def _auth_url_for(client: Any) -> str | None:
    for key in (
        "authUrl",
        "authorizationUrl",
        "authorizeUrl",
        "oauthUrl",
        "loginUrl",
        "idp_url",
        "idpUrl",
        "url",
    ):
        value = _client_value(client, key)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    config = _client_value(client, "config")
    if isinstance(config, dict):
        for key in ("authUrl", "authorizationUrl", "authorizeUrl", "oauthUrl", "loginUrl", "idp_url", "idpUrl", "url"):
            value = config.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value
    return None


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    server_name = input_data.get("server")
    token = input_data.get("token")
    mcp_clients = _get_mcp_clients(context)

    client = next((item for item in mcp_clients if _client_value(item, "name") == server_name), None)
    if client is None:
        available = ", ".join(str(_client_value(item, "name", "")) for item in mcp_clients if _client_value(item, "name"))
        return {"authenticated": False, "status": "error", "message": f'Server "{server_name}" not found. Available servers: {available}'}

    if _client_value(client, "type") == "vivianai-proxy":
        return {
            "authenticated": False,
            "status": "unsupported",
            "message": f'This is a api-vivian.d0a.net MCP connector. Ask the user to run /mcp and select "{server_name}" to authenticate.',
        }

    if token:
        try:
            applied = await _set_client_token(client, str(token))
            if not applied:
                return {
                    "authenticated": False,
                    "status": "unsupported",
                    "message": f'Server "{server_name}" does not expose a token-auth interface in this Python context. Run /mcp to authenticate manually.',
                }
            await _reconnect_client(client)
            return {
                "authenticated": True,
                "status": "authenticated",
                "message": f'Applied credentials for MCP server "{server_name}".',
            }
        except Exception as exc:
            return {
                "authenticated": False,
                "status": "error",
                "message": f'Failed to authenticate MCP server "{server_name}": {exc}',
            }

    auth_url = _auth_url_for(client)
    if auth_url:
        return {
            "authenticated": False,
            "status": "auth_url",
            "authUrl": auth_url,
            "message": f'Ask the user to open this URL to authenticate the MCP server "{server_name}":\n\n{auth_url}',
        }

    transport = _client_value(client, "transport") or _client_value(client, "type") or "configured transport"
    return {
        "authenticated": False,
        "status": "unsupported",
        "message": f'MCP server "{server_name}" uses {transport} and does not expose a programmatic auth flow in this Python context. Run /mcp and authenticate manually, or provide a token to this tool if the server accepts token auth.',
    }
