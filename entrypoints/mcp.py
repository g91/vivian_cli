"""MCP entrypoint — mirrors src/entrypoints/mcp.ts."""
from __future__ import annotations

import os
from pathlib import Path


async def startMCPServer(cwd: str, debug: bool, verbose: bool) -> None:
    del debug, verbose

    target_cwd = str(Path(cwd).resolve())
    os.chdir(target_cwd)

    if os.environ.get("VIVIAN_COMPUTER_USE_MCP") == "1":
        from ..utils.computerUse.mcpServer import runComputerUseMcpServer

        await runComputerUseMcpServer()
        return

    if os.environ.get("VIVIAN_CHROME_MCP") == "1":
        from ..utils.vivianInChrome.mcpServer import runvivianInChromeMcpServer

        await runvivianInChromeMcpServer()
        return

    raise RuntimeError(
        "No Python MCP server backend is configured. Set VIVIAN_COMPUTER_USE_MCP=1 "
        "or VIVIAN_CHROME_MCP=1 to start an available backend."
    )


async def mcpMain() -> None:
    """MCP server entrypoint."""
    await startMCPServer(os.getcwd(), debug=False, verbose=False)


start_mcp_server = startMCPServer
