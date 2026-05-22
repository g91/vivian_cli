"""Port of src/utils/swarm/teammateLayoutManager.ts."""
from __future__ import annotations

from .backends.detection import isInsideTmux as _is_inside_tmux
from .backends.registry import detectAndGetBackend


_PALETTE = ["red", "blue", "green", "yellow", "purple", "orange", "pink", "cyan"]
_assigned_colors: dict[str, str] = {}
_color_index = 0


async def getBackend():
    detection = await detectAndGetBackend()
    return detection["backend"]


def assignTeammateColor(teammateId):
    global _color_index
    key = str(teammateId)
    existing = _assigned_colors.get(key)
    if existing:
        return existing
    color = _PALETTE[_color_index % len(_PALETTE)]
    _assigned_colors[key] = color
    _color_index += 1
    return color


def getTeammateColor(teammateId):
    return _assigned_colors.get(str(teammateId))


def clearTeammateColors():
    global _color_index
    _assigned_colors.clear()
    _color_index = 0


async def isInsideTmux():
    return await _is_inside_tmux()


async def createTeammatePaneInSwarmView(teammateName, teammateColor):
    backend = await getBackend()
    return await backend.createTeammatePaneInSwarmView(teammateName, teammateColor)


async def enablePaneBorderStatus(windowTarget=None, useSwarmSocket=False):
    backend = await getBackend()
    return await backend.enablePaneBorderStatus(windowTarget, useSwarmSocket)


async def sendCommandToPane(paneId, command, useSwarmSocket=False):
    backend = await getBackend()
    return await backend.sendCommandToPane(paneId, command, useSwarmSocket)


get_backend = getBackend
assign_teammate_color = assignTeammateColor
get_teammate_color = getTeammateColor
clear_teammate_colors = clearTeammateColors
is_inside_tmux = isInsideTmux
create_teammate_pane_in_swarm_view = createTeammatePaneInSwarmView
enable_pane_border_status = enablePaneBorderStatus
send_command_to_pane = sendCommandToPane