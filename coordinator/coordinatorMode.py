"""Coordinator mode — mirrors src/coordinator/coordinatorMode.ts."""
from __future__ import annotations

import os
from typing import Optional


def isCoordinatorMode() -> bool:
    """Check if coordinator mode is active."""
    return os.environ.get("vivian_CODE_COORDINATOR_MODE", "") == "1"


def matchSessionMode(session_mode: Optional[str]) -> Optional[str]:
    """Match coordinator mode to session's stored mode."""
    if not session_mode:
        return None
    current = isCoordinatorMode()
    session_is_coordinator = session_mode == "coordinator"
    if current == session_is_coordinator:
        return None
    if session_is_coordinator:
        os.environ["vivian_CODE_COORDINATOR_MODE"] = "1"
    else:
        os.environ.pop("vivian_CODE_COORDINATOR_MODE", None)
    return (
        "Entered coordinator mode to match resumed session."
        if session_is_coordinator
        else "Exited coordinator mode to match resumed session."
    )


def getCoordinatorUserContext(
    mcp_clients: list = None,
    scratchpad_dir: Optional[str] = None,
) -> dict:
    """Get coordinator user context."""
    if not isCoordinatorMode():
        return {}
    mcp_clients = mcp_clients or []
    worker_tools = "Bash, Read, Edit"
    content = f"Workers spawned via the Agent tool have access to these tools: {worker_tools}"
    if mcp_clients:
        server_names = ", ".join(c.get("name", "") for c in mcp_clients)
        content += f"\nMCP servers available: {server_names}"
    if scratchpad_dir:
        content += f"\nScratchpad directory: {scratchpad_dir}"
    return {"coordinatorContext": content}


is_coordinator_mode = isCoordinatorMode
match_session_mode = matchSessionMode
get_coordinator_user_context = getCoordinatorUserContext
