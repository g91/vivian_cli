"""mcp command — mirrors src/commands/mcp/mcp.tsx.

Manage MCP (Model Context Protocol) server connections.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...services.mcp import getMcpPrefix, mcpInfoFromString

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def call(args: str, context: CommandContext) -> TextResult:
    """Manage MCP servers."""
    from ...types.command import TextResult
    parts = args.strip().split(maxsplit=2) if args.strip() else []
    action = parts[0].lower() if parts else ""

    if not action or action == "status":
        return TextResult(_show_mcp_status(context))

    if action == "info" and len(parts) >= 2:
        tool_str = parts[1]
        info = mcpInfoFromString(tool_str)
        if info:
            return TextResult(f"Server: {info['serverName']}\nTool:   {info['toolName']}")
        return TextResult("Not a valid MCP tool name (expected: mcp__server__tool)")

    if action == "prefix" and len(parts) >= 2:
        return TextResult(f"Prefix: {getMcpPrefix(parts[1])}")

    if action == "add" and len(parts) >= 3:
        name, command = parts[1], parts[2]
        servers = _get_servers(context)
        servers[name] = {"command": command, "enabled": True}
        _save_servers(context, servers)
        return TextResult(f"MCP server added: {name} → {command}")

    if action == "remove" and len(parts) >= 2:
        name = parts[1]
        servers = _get_servers(context)
        if name in servers:
            del servers[name]
            _save_servers(context, servers)
            return TextResult(f"MCP server removed: {name}")
        return TextResult(f"No MCP server named: {name}")

    if action == "enable" and len(parts) >= 2:
        name = parts[1]
        servers = _get_servers(context)
        if name in servers:
            servers[name]["enabled"] = True
            _save_servers(context, servers)
            return TextResult(f"MCP server enabled: {name}")
        return TextResult(f"No MCP server named: {name}")

    if action == "disable" and len(parts) >= 2:
        name = parts[1]
        servers = _get_servers(context)
        if name in servers:
            servers[name]["enabled"] = False
            _save_servers(context, servers)
            return TextResult(f"MCP server disabled: {name}")
        return TextResult(f"No MCP server named: {name}")

    return TextResult(
        "Usage: /mcp [status|info <tool_name>|prefix <server_name>|add <name> <cmd>|remove <name>|enable <name>|disable <name>]"
    )


def _get_servers(context: CommandContext) -> dict:
    try:
        servers = getattr(context, "config", {}).get("mcp_servers", {})
        if isinstance(servers, dict):
            return {name: dict(cfg) if isinstance(cfg, dict) else cfg for name, cfg in servers.items()}
        return {}
    except Exception:
        return {}


def _save_servers(context: CommandContext, servers: dict) -> None:
    try:
        if hasattr(context, "set_setting"):
            context.set_setting("mcp_servers", servers)
    except Exception:
        pass


def _show_mcp_status(context: CommandContext) -> str:
    servers = _get_servers(context)
    if not servers:
        return "No MCP servers configured.\nUse /mcp add <name> <command> to add one."
    lines = ["MCP Servers:", ""]
    for name, cfg in servers.items():
        status = "✓ enabled" if cfg.get("enabled", True) else "✗ disabled"
        lines.append(f"  {name}: {cfg.get('command', '?')} ({status})")
    return "\n".join(lines)


showMcpStatus = _show_mcp_status
show_mcp_status = _show_mcp_status
