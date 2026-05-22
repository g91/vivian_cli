"""MCP subcommand handlers — mirrors src/cli/handlers/mcp.tsx.

Handles ``vivian mcp`` subcommands: add, remove, list, get, reset.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..exit import cli_error, cli_ok

_SETTINGS_FILE = Path.home() / ".vivian" / "settings.json"


def _load_settings() -> dict:
    try:
        return json.loads(_SETTINGS_FILE.read_text())
    except Exception:
        return {}


def _save_settings(data: dict) -> None:
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(json.dumps(data, indent=2))


def mcp_list_handler() -> None:
    """List all configured MCP servers."""
    settings = _load_settings()
    servers: dict = settings.get("mcpServers") or {}
    if not servers:
        print("No MCP servers configured.")
        return
    for name, cfg in sorted(servers.items()):
        if isinstance(cfg, dict):
            cmd = cfg.get("command", "?")
            args = " ".join(cfg.get("args", []))
            scope = cfg.get("scope", "user")
            print(f"  {name}  [{scope}]  {cmd} {args}".rstrip())
        else:
            print(f"  {name}: {cfg}")


def mcp_get_handler(server_name: str) -> None:
    """Print configuration for a specific MCP server."""
    settings = _load_settings()
    servers: dict = settings.get("mcpServers") or {}
    if server_name not in servers:
        cli_error(f"MCP server '{server_name}' not found.")
    print(json.dumps({server_name: servers[server_name]}, indent=2))


def mcp_add_handler(
    server_name: str,
    command: str,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    scope: str = "user",
) -> None:
    """Add or update an MCP server configuration."""
    settings = _load_settings()
    servers: dict = settings.setdefault("mcpServers", {})
    servers[server_name] = {
        "command": command,
        "args": args or [],
        **({"env": env} if env else {}),
        "scope": scope,
    }
    _save_settings(settings)
    print(f"✔ MCP server '{server_name}' added.")


def mcp_remove_handler(server_name: str) -> None:
    """Remove an MCP server configuration."""
    settings = _load_settings()
    servers: dict = settings.get("mcpServers") or {}
    if server_name not in servers:
        cli_error(f"MCP server '{server_name}' not found.")
    servers.pop(server_name)
    settings["mcpServers"] = servers
    _save_settings(settings)
    print(f"✔ MCP server '{server_name}' removed.")


def mcp_reset_handler() -> None:
    """Remove all MCP server configurations."""
    settings = _load_settings()
    count = len(settings.get("mcpServers") or {})
    settings["mcpServers"] = {}
    _save_settings(settings)
    print(f"✔ Removed {count} MCP server configuration(s).")
