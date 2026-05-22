"""Port of src/utils/computerUse/common.ts."""
from __future__ import annotations

import os

from ...services.mcp.normalization import normalizeNameForMCP
from ..env import env


COMPUTER_USE_MCP_SERVER_NAME = "computer-use"
CLI_HOST_BUNDLE_ID = "com.anthropic.vivian-code.cli-no-window"
TERMINAL_BUNDLE_ID_FALLBACK = {
    "iTerm.app": "com.googlecode.iterm2",
    "Apple_Terminal": "com.apple.Terminal",
    "ghostty": "com.mitchellh.ghostty",
    "kitty": "net.kovidgoyal.kitty",
    "WarpTerminal": "dev.warp.Warp-Stable",
    "vscode": "com.microsoft.VSCode",
}
CLI_CU_CAPABILITIES = {
    "screenshotFiltering": "native",
    "platform": "darwin",
}


def getTerminalBundleId():
    cf_bundle_id = os.environ.get("__CFBundleIdentifier")
    if cf_bundle_id:
        return cf_bundle_id
    terminal_name = getattr(env, "terminal", None)
    return TERMINAL_BUNDLE_ID_FALLBACK.get(terminal_name or "")


def isComputerUseMCPServer(name):
    return normalizeNameForMCP(name) == COMPUTER_USE_MCP_SERVER_NAME


get_terminal_bundle_id = getTerminalBundleId
is_computer_use_mcp_server = isComputerUseMCPServer

