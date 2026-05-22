"""Port of src/utils/swarm/constants.ts."""
from __future__ import annotations

import os


TEAM_LEAD_NAME = "team-lead"
SWARM_SESSION_NAME = "vivian-swarm"
SWARM_VIEW_WINDOW_NAME = "swarm-view"
TMUX_COMMAND = "tmux"
HIDDEN_SESSION_NAME = "vivian-hidden"


def getSwarmSocketName() -> str:
    return f"vivian-swarm-{os.getpid()}"


TEAMMATE_COMMAND_ENV_VAR = "vivian_CODE_TEAMMATE_COMMAND"
TEAMMATE_COLOR_ENV_VAR = "vivian_CODE_AGENT_COLOR"
PLAN_MODE_REQUIRED_ENV_VAR = "vivian_CODE_PLAN_MODE_REQUIRED"


get_swarm_socket_name = getSwarmSocketName