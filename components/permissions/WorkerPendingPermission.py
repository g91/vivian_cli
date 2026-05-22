"""Compact pending-permission card for swarm workers."""

from __future__ import annotations

from dataclasses import dataclass

from ...utils.teammate import getAgentName, getTeammateColor, getTeamName
from ..Spinner import Spinner
from ..design_system import Pane
from .WorkerBadge import WorkerBadge


@dataclass(slots=True)
class WorkerPendingPermission:
    toolName: str
    description: str

    def render_lines(self) -> list[str]:
        team_name = getTeamName()
        agent_name = getAgentName()
        agent_color = getTeammateColor()
        lines = [f"{Spinner()} Waiting for team lead approval"]
        if agent_name and agent_color:
            lines.extend(WorkerBadge(name=agent_name, color=agent_color).render_lines())
        lines.append(f"Tool: {self.toolName}")
        lines.append(f"Action: {self.description}")
        if team_name:
            lines.append(f'Permission request sent to team "{team_name}" leader')
        return Pane(children=lines, color="warning").render_lines()


__all__ = ["WorkerPendingPermission"]