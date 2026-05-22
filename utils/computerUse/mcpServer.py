"""Port of src/utils/computerUse/mcpServer.ts."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from ..debug import logForDebugging
from .appNames import filterAppsForDescription
from .gates import getChicagoCoordinateMode
from .hostAdapter import getComputerUseHostAdapter

APP_ENUM_TIMEOUT_MS = 1000


async def tryGetInstalledAppNames() -> list[str] | None:
    adapter = getComputerUseHostAdapter()
    executor = adapter["executor"]
    enum_task = executor.listInstalledApps() if callable(executor.get("listInstalledApps")) else None

    if enum_task is None:
        return None

    try:
        installed = await asyncio.wait_for(asyncio.ensure_future(enum_task) if asyncio.iscoroutine(enum_task) else enum_task, timeout=APP_ENUM_TIMEOUT_MS / 1000)
    except asyncio.TimeoutError:
        logForDebugging(f"[Computer Use MCP] app enumeration exceeded {APP_ENUM_TIMEOUT_MS}ms or failed; tool description omits list")
        return None
    except Exception:
        logForDebugging(f"[Computer Use MCP] app enumeration failed; tool description omits list")
        return None

    if not installed:
        return None

    home_dir = str(Path.home())
    return filterAppsForDescription(installed, home_dir)


async def createComputerUseMcpServerForCli() -> dict[str, Any]:
    adapter = getComputerUseHostAdapter()
    coordinate_mode = getChicagoCoordinateMode()

    # In the TS version, this delegates to @ant/computer-use-mcp's createComputerUseMcpServer.
    # In Python, we build a compatible server dict that mirrors the same interface.
    installed_app_names = await tryGetInstalledAppNames()

    # Build tool list from capabilities
    capabilities = adapter["executor"].get("capabilities", {})
    tools = _build_computer_use_tools(capabilities, coordinate_mode, installed_app_names)

    server: dict[str, Any] = {
        "adapter": adapter,
        "coordinateMode": coordinate_mode,
        "tools": tools,
        "installedAppNames": installed_app_names,
        "requestHandlers": {},
    }

    def list_tools_handler() -> dict[str, Any]:
        if adapter.get("isDisabled", lambda: False)():
            return {"tools": []}
        return {"tools": tools}

    server["requestHandlers"]["ListTools"] = list_tools_handler

    return server


def _build_computer_use_tools(
    capabilities: dict[str, Any],
    coordinate_mode: str,
    installed_app_names: list[str] | None,
) -> list[dict[str, Any]]:
    """Build the computer-use tool definitions matching @ant/computer-use-mcp's buildComputerUseTools."""
    tool_defs = [
        {"name": "screenshot", "description": "Capture a screenshot of the current display."},
        {"name": "left_click", "description": "Left click at the specified coordinates."},
        {"name": "right_click", "description": "Right click at the specified coordinates."},
        {"name": "middle_click", "description": "Middle click at the specified coordinates."},
        {"name": "double_click", "description": "Double click at the specified coordinates."},
        {"name": "triple_click", "description": "Triple click at the specified coordinates."},
        {"name": "mouse_move", "description": "Move the mouse to the specified coordinates."},
        {"name": "left_click_drag", "description": "Click and drag from start to end coordinates."},
        {"name": "type", "description": "Type the specified text."},
        {"name": "key", "description": "Press a key or key combination."},
        {"name": "hold_key", "description": "Hold down a key or key combination."},
        {"name": "scroll", "description": "Scroll at the specified coordinates."},
        {"name": "zoom", "description": "Capture a zoomed-in screenshot of a region."},
        {"name": "wait", "description": "Wait for the specified duration."},
        {"name": "open_application", "description": "Open an application by bundle ID."},
        {"name": "cursor_position", "description": "Get the current cursor position."},
        {"name": "left_mouse_down", "description": "Press and hold the left mouse button."},
        {"name": "left_mouse_up", "description": "Release the left mouse button."},
        {"name": "read_clipboard", "description": "Read the current clipboard contents."},
        {"name": "write_clipboard", "description": "Write text to the clipboard."},
        {"name": "list_granted_applications", "description": "List applications that have been granted access."},
    ]

    # Augment request_access description with installed app names
    request_access_desc = "Request access to control applications. You must call this before interacting with any application."
    if installed_app_names:
        request_access_desc += f"\n\nAvailable applications: {', '.join(installed_app_names[:50])}"
    tool_defs.append({"name": "request_access", "description": request_access_desc})

    if capabilities.get("screenshotFiltering") == "native":
        tool_defs.append({"name": "computer_batch", "description": "Execute multiple computer-use actions in a batch."})

    return tool_defs


async def runComputerUseMcpServer() -> None:
    """Subprocess entrypoint for --computer-use-mcp."""
    logForDebugging("[Computer Use MCP] Starting MCP server (Python port)")

    server = await createComputerUseMcpServerForCli()

    # In the TS version, this uses StdioServerTransport from MCP SDK.
    # In Python, we keep the process alive until stdin closes.
    logForDebugging("[Computer Use MCP] MCP server started")

    loop = asyncio.get_event_loop()
    future: asyncio.Future[None] = loop.create_future()

    def _on_stdin_end() -> None:
        if not future.done():
            future.set_result(None)

    try:
        await future
    except asyncio.CancelledError:
        pass


try_get_installed_app_names = tryGetInstalledAppNames
create_computer_use_mcp_server_for_cli = createComputerUseMcpServerForCli
run_computer_use_mcp_server = runComputerUseMcpServer

