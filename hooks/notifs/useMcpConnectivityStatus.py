"""MCP connectivity status — mirrors src/hooks/notifs/useMcpConnectivityStatus.ts."""
from __future__ import annotations

def useMcpConnectivityStatus(connected: bool = True) -> dict:
    """Display MCP connection status."""
    return {
        "connected": connected,
        "status": "Connected" if connected else "Disconnected",
    }

use_mcp_connectivity_status = useMcpConnectivityStatus
