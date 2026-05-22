"""xaaIdpCommand — mirrors src/commands/mcp/xaaIdpCommand.ts.

XAA Identity Provider command for MCP authentication.
"""

from __future__ import annotations


def xaa_idp_command(idp_url: str = "", client_id: str = "") -> dict:
    """Build an XAA IDP command configuration."""
    return {
        "type": "xaa_idp",
        "idp_url": idp_url,
        "client_id": client_id,
    }
