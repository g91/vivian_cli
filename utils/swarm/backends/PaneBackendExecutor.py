"""Port of src/utils/swarm/backends/PaneBackendExecutor.ts."""
from __future__ import annotations

from ....bootstrap.state import getSessionId
from ...agentId import format_agent_id, parse_agent_id
from ...bash.shellQuote import quote
from ...cleanupRegistry import register_cleanup
from ...debug import logForDebugging
from ...slowOperations import jsonStringify
from ..spawnUtils import buildInheritedCliFlags, buildInheritedEnvVars, getTeammateCommand
from .detection import isInsideTmux


class PaneBackendExecutor:
    def __init__(self, backend):
        self.backend = backend
        self.type = getattr(backend, "type", None)
        self.context = None
        self.spawnedTeammates: dict[str, dict[str, object]] = {}
        self.cleanupRegistered = False

    def setContext(self, context) -> None:
        self.context = context

    async def isAvailable(self):
        return await self.backend.isAvailable()

    async def spawn(self, config):
        from ...teammateMailbox import writeToMailbox
        from ..teammateLayoutManager import assignTeammateColor

        agent_id = format_agent_id(_cfg(config, "name"), _cfg(config, "teamName"))

        if self.context is None:
            logForDebugging(
                f"[PaneBackendExecutor] spawn() called without context for {_cfg(config, 'name')}"
            )
            return {
                "success": False,
                "agentId": agent_id,
                "error": "PaneBackendExecutor not initialized. Call setContext() before spawn().",
            }

        try:
            teammate_color = _cfg(config, "color") or assignTeammateColor(agent_id)
            pane = await self.backend.createTeammatePaneInSwarmView(_cfg(config, "name"), teammate_color)
            pane_id = pane["paneId"]
            is_first_teammate = bool(pane.get("isFirstTeammate"))
            inside_tmux = await isInsideTmux()

            if is_first_teammate and inside_tmux:
                await self.backend.enablePaneBorderStatus()

            binary_path = getTeammateCommand()
            parent_session_id = _cfg(config, "parentSessionId") or getSessionId()
            teammate_args = " ".join(
                part
                for part in [
                    f"--agent-id {quote([agent_id])}",
                    f"--agent-name {quote([_cfg(config, 'name')])}",
                    f"--team-name {quote([_cfg(config, 'teamName')])}",
                    f"--agent-color {quote([teammate_color])}",
                    f"--parent-session-id {quote([parent_session_id])}",
                    "--plan-mode-required" if _cfg(config, "planModeRequired") else "",
                ]
                if part
            )

            app_state = self.context.getAppState()
            permission_mode = _get_permission_mode(app_state)
            inherited_flags = buildInheritedCliFlags(
                {
                    "planModeRequired": _cfg(config, "planModeRequired"),
                    "permissionMode": permission_mode,
                }
            )
            model = _cfg(config, "model")
            if model:
                inherited_flags = f"{inherited_flags} --model {quote([model])}".strip()

            flags_str = f" {inherited_flags}" if inherited_flags else ""
            working_dir = _cfg(config, "cwd") or "."
            env_str = buildInheritedEnvVars()
            spawn_command = (
                f"cd {quote([working_dir])} && env {env_str} {quote([binary_path])} {teammate_args}{flags_str}"
            )

            await self.backend.sendCommandToPane(pane_id, spawn_command, not inside_tmux)
            self.spawnedTeammates[agent_id] = {"paneId": pane_id, "insideTmux": inside_tmux}

            if not self.cleanupRegistered:
                self.cleanupRegistered = True

                async def _cleanup() -> None:
                    for teammate_id, info in list(self.spawnedTeammates.items()):
                        logForDebugging(
                            f"[PaneBackendExecutor] Cleanup: killing pane for {teammate_id}"
                        )
                        await self.backend.killPane(info["paneId"], not bool(info["insideTmux"]))
                    self.spawnedTeammates.clear()

                register_cleanup(_cleanup)

            await writeToMailbox(
                _cfg(config, "name"),
                {
                    "from": "team-lead",
                    "text": _cfg(config, "prompt"),
                    "timestamp": _now_iso(),
                },
                _cfg(config, "teamName"),
            )

            logForDebugging(f"[PaneBackendExecutor] Spawned teammate {agent_id} in pane {pane_id}")
            return {"success": True, "agentId": agent_id, "paneId": pane_id}
        except Exception as error:
            error_message = str(error)
            logForDebugging(f"[PaneBackendExecutor] Failed to spawn {agent_id}: {error_message}")
            return {"success": False, "agentId": agent_id, "error": error_message}

    async def sendMessage(self, agentId, message):
        from ...teammateMailbox import writeToMailbox

        parsed = parse_agent_id(agentId)
        if not parsed:
            raise RuntimeError(
                f"Invalid agentId format: {agentId}. Expected format: agentName@teamName"
            )
        await writeToMailbox(
            parsed["agent_name"],
            {
                "text": _msg_get(message, "text"),
                "from": _msg_get(message, "from"),
                "color": _msg_get(message, "color"),
                "timestamp": _msg_get(message, "timestamp") or _now_iso(),
            },
            parsed["team_name"],
        )

    async def terminate(self, agentId, reason=None):
        from ...teammateMailbox import writeToMailbox

        parsed = parse_agent_id(agentId)
        if not parsed:
            return False
        shutdown_request = {
            "type": "shutdown_request",
            "requestId": f"shutdown-{agentId}",
            "from": "team-lead",
            "reason": reason,
        }
        await writeToMailbox(
            parsed["agent_name"],
            {
                "from": "team-lead",
                "text": jsonStringify(shutdown_request),
                "timestamp": _now_iso(),
            },
            parsed["team_name"],
        )
        return True

    async def kill(self, agentId):
        teammate_info = self.spawnedTeammates.get(agentId)
        if not teammate_info:
            return False
        killed = await self.backend.killPane(teammate_info["paneId"], not bool(teammate_info["insideTmux"]))
        if killed:
            self.spawnedTeammates.pop(agentId, None)
        return bool(killed)

    async def isActive(self, agentId):
        return agentId in self.spawnedTeammates


def createPaneBackendExecutor(backend):
    return PaneBackendExecutor(backend)


def _cfg(config, key):
    if isinstance(config, dict):
        return config.get(key)
    return getattr(config, key, None)


def _get_permission_mode(app_state):
    if isinstance(app_state, dict):
        tool_permission_context = app_state.get("toolPermissionContext", {})
        if isinstance(tool_permission_context, dict):
            return tool_permission_context.get("mode")
        return getattr(tool_permission_context, "mode", None)
    tool_permission_context = getattr(app_state, "toolPermissionContext", None)
    if isinstance(tool_permission_context, dict):
        return tool_permission_context.get("mode")
    return getattr(tool_permission_context, "mode", None)


def _msg_get(message, key):
    if isinstance(message, dict):
        return message.get(key)
    return getattr(message, key, None)


def _now_iso():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


create_pane_backend_executor = createPaneBackendExecutor