"""Standalone agent helpers — mirrors src/utils/standaloneAgent.ts"""
from __future__ import annotations

from typing import Optional


def get_standalone_agent_name(app_state: dict) -> Optional[str]:
    """Return the standalone agent name from app state, if any.

    Returns None if a team name is set (i.e. swarm mode is active).
    """
    # If team name is set, we're in swarm mode — no standalone agent
    if app_state.get("team_name"):
        return None
    ctx = app_state.get("standalone_agent_context") or {}
    return ctx.get("name")
