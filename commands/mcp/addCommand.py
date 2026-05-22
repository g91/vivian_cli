"""addCommand — mirrors src/commands/mcp/addCommand.ts.

Add a new MCP server command.
"""

from __future__ import annotations


def add_mcp_command(name: str, command: str, args: list[str] | None = None) -> dict:
    """Build an MCP server command configuration."""
    return {
        "name": name,
        "command": command,
        "args": args or [],
        "enabled": True,
    }
