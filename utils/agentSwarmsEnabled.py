"""Agent swarms feature gate — mirrors src/utils/agentSwarmsEnabled.ts"""
from __future__ import annotations

import os
import sys

from .envUtils import is_env_truthy


def is_agent_swarms_enabled() -> bool:
    """Return True if the agent teams / swarm feature is enabled.

    Internal users (USER_TYPE=ant) always have it enabled.
    External users need vivian_CODE_EXPERIMENTAL_AGENT_TEAMS=1 or the
    --agent-teams flag.
    """
    if os.environ.get("USER_TYPE") == "ant":
        return True
    if not (
        is_env_truthy(os.environ.get("vivian_CODE_EXPERIMENTAL_AGENT_TEAMS"))
        or "--agent-teams" in sys.argv
    ):
        return False
    return True
