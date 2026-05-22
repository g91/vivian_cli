"""Port of src/utils/computerUse/setup.ts."""
from __future__ import annotations

from pathlib import Path
import sys

from ...services.mcp.mcpStringUtils import buildMcpToolName
from ..bundledMode import is_in_bundled_mode
from .common import CLI_CU_CAPABILITIES, COMPUTER_USE_MCP_SERVER_NAME
from .gates import getChicagoCoordinateMode


COMPUTER_USE_TOOL_NAMES = [
    "screenshot",
    "zoom",
    "request_access",
    "list_granted_applications",
    "left_click",
    "right_click",
    "middle_click",
    "double_click",
    "triple_click",
    "left_mouse_down",
    "left_mouse_up",
    "mouse_move",
    "left_click_drag",
    "type",
    "key",
    "hold_key",
    "scroll",
    "wait",
    "read_clipboard",
    "write_clipboard",
    "open_application",
    "cursor_position",
    "computer_batch",
]


def setupComputerUseMCP():
    allowed_tools = [buildMcpToolName(COMPUTER_USE_MCP_SERVER_NAME, name) for name in COMPUTER_USE_TOOL_NAMES]
    if is_in_bundled_mode():
        args = ["--computer-use-mcp"]
    else:
        cli_path = Path(__file__).resolve().parents[2] / "cli.py"
        args = [str(cli_path), "--computer-use-mcp"]
    return {
        "mcpConfig": {
            COMPUTER_USE_MCP_SERVER_NAME: {
                "type": "stdio",
                "command": sys.executable,
                "args": args,
                "scope": "dynamic",
                "capabilities": CLI_CU_CAPABILITIES,
                "coordinateMode": getChicagoCoordinateMode(),
            }
        },
        "allowedTools": allowed_tools,
    }


setup_computer_use_mcp = setupComputerUseMCP

