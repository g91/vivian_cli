"""Port of src/utils/swarm/backends/TmuxBackend.ts."""
from __future__ import annotations

import asyncio

from ...debug import logForDebugging
from ...execFileNoThrow import exec_file_no_throw
from ...sleep import sleep
from ..constants import (
    HIDDEN_SESSION_NAME,
    SWARM_SESSION_NAME,
    SWARM_VIEW_WINDOW_NAME,
    TMUX_COMMAND,
    getSwarmSocketName,
)
from .detection import getLeaderPaneId, isInsideTmux, isTmuxAvailable
from .registry import registerTmuxBackend


_first_pane_used_for_external = False
_cached_leader_window_target: str | None = None
_pane_creation_lock = asyncio.Lock()
PANE_SHELL_INIT_DELAY_MS = 200


async def waitForPaneShellReady():
    await sleep(PANE_SHELL_INIT_DELAY_MS)


async def acquirePaneCreationLock():
    await _pane_creation_lock.acquire()

    def _release() -> None:
        if _pane_creation_lock.locked():
            _pane_creation_lock.release()

    return _release


def getTmuxColorName(color):
    tmux_colors = {
        "red": "red",
        "blue": "blue",
        "green": "green",
        "yellow": "yellow",
        "purple": "magenta",
        "orange": "colour208",
        "pink": "colour205",
        "cyan": "cyan",
    }
    return tmux_colors.get(color, "cyan")


async def runTmuxInUserSession(args):
    return await exec_file_no_throw(TMUX_COMMAND, args)


async def runTmuxInSwarm(args):
    return await exec_file_no_throw(TMUX_COMMAND, ["-L", getSwarmSocketName(), *args])


class TmuxBackend:
    def __init__(self):
        self.type = "tmux"
        self.displayName = "tmux"
        self.supportsHideShow = True

    async def isAvailable(self):
        return await isTmuxAvailable()

    async def isRunningInside(self):
        return await isInsideTmux()

    async def createTeammatePaneInSwarmView(self, name, color):
        release_lock = await acquirePaneCreationLock()
        try:
            if await self.isRunningInside():
                return await self._create_teammate_pane_with_leader(name, color)
            return await self._create_teammate_pane_external(name, color)
        finally:
            release_lock()

    async def sendCommandToPane(self, paneId, command, useExternalSession=False):
        run_tmux = runTmuxInSwarm if useExternalSession else runTmuxInUserSession
        result = await run_tmux(["send-keys", "-t", paneId, command, "Enter"])
        if result.get("code") != 0:
            raise RuntimeError(
                f"Failed to send command to pane {paneId}: {result.get('stderr', '')}"
            )

    async def setPaneBorderColor(self, paneId, color, useExternalSession=False):
        tmux_color = getTmuxColorName(color)
        run_tmux = runTmuxInSwarm if useExternalSession else runTmuxInUserSession
        await run_tmux(["select-pane", "-t", paneId, "-P", f"bg=default,fg={tmux_color}"])
        await run_tmux(["set-option", "-p", "-t", paneId, "pane-border-style", f"fg={tmux_color}"])
        await run_tmux(["set-option", "-p", "-t", paneId, "pane-active-border-style", f"fg={tmux_color}"])

    async def setPaneTitle(self, paneId, name, color, useExternalSession=False):
        tmux_color = getTmuxColorName(color)
        run_tmux = runTmuxInSwarm if useExternalSession else runTmuxInUserSession
        await run_tmux(["select-pane", "-t", paneId, "-T", name])
        await run_tmux([
            "set-option",
            "-p",
            "-t",
            paneId,
            "pane-border-format",
            f"#[fg={tmux_color},bold] #{{pane_title}} #[default]",
        ])

    async def enablePaneBorderStatus(self, windowTarget=None, useExternalSession=False):
        target = windowTarget or await self._get_current_window_target()
        if not target:
            return
        run_tmux = runTmuxInSwarm if useExternalSession else runTmuxInUserSession
        await run_tmux(["set-option", "-w", "-t", target, "pane-border-status", "top"])

    async def rebalancePanes(self, windowTarget, hasLeader):
        run_tmux = runTmuxInUserSession if await self.isRunningInside() else runTmuxInSwarm
        layout = "main-vertical" if hasLeader else "tiled"
        await run_tmux(["select-layout", "-t", windowTarget, layout])
        if hasLeader:
            panes_result = await run_tmux(["list-panes", "-t", windowTarget, "-F", "#{pane_id}"])
            panes = [pane for pane in panes_result.get("stdout", "").splitlines() if pane.strip()]
            if panes:
                await run_tmux(["resize-pane", "-t", panes[0], "-x", "30%"])

    async def killPane(self, paneId, useExternalSession=False):
        run_tmux = runTmuxInSwarm if useExternalSession else runTmuxInUserSession
        result = await run_tmux(["kill-pane", "-t", paneId])
        return result.get("code") == 0

    async def hidePane(self, paneId, useExternalSession=False):
        run_tmux = runTmuxInSwarm if useExternalSession else runTmuxInUserSession
        await run_tmux(["new-session", "-d", "-s", HIDDEN_SESSION_NAME])
        result = await run_tmux(["break-pane", "-d", "-s", paneId, "-t", f"{HIDDEN_SESSION_NAME}:"])
        if result.get("code") == 0:
            logForDebugging(f"[TmuxBackend] Hidden pane {paneId}")
            return True
        logForDebugging(f"[TmuxBackend] Failed to hide pane {paneId}: {result.get('stderr', '')}")
        return False

    async def showPane(self, paneId, targetWindowOrPane, useExternalSession=False):
        run_tmux = runTmuxInSwarm if useExternalSession else runTmuxInUserSession
        result = await run_tmux(["join-pane", "-h", "-s", paneId, "-t", targetWindowOrPane])
        if result.get("code") != 0:
            logForDebugging(f"[TmuxBackend] Failed to show pane {paneId}: {result.get('stderr', '')}")
            return False
        await run_tmux(["select-layout", "-t", targetWindowOrPane, "main-vertical"])
        panes_result = await run_tmux(["list-panes", "-t", targetWindowOrPane, "-F", "#{pane_id}"])
        panes = [pane for pane in panes_result.get("stdout", "").splitlines() if pane.strip()]
        if panes:
            await run_tmux(["resize-pane", "-t", panes[0], "-x", "30%"])
        return True

    async def _get_current_pane_id(self):
        leader_pane = getLeaderPaneId()
        if leader_pane:
            return leader_pane
        result = await exec_file_no_throw(TMUX_COMMAND, ["display-message", "-p", "#{pane_id}"])
        if result.get("code") != 0:
            return None
        return result.get("stdout", "").strip() or None

    async def _get_current_window_target(self):
        global _cached_leader_window_target
        if _cached_leader_window_target:
            return _cached_leader_window_target
        leader_pane = getLeaderPaneId()
        args = ["display-message"]
        if leader_pane:
            args.extend(["-t", leader_pane])
        args.extend(["-p", "#{session_name}:#{window_index}"])
        result = await exec_file_no_throw(TMUX_COMMAND, args)
        if result.get("code") != 0:
            return None
        _cached_leader_window_target = result.get("stdout", "").strip() or None
        return _cached_leader_window_target

    async def _get_current_window_pane_count(self, windowTarget=None, useSwarmSocket=False):
        target = windowTarget or await self._get_current_window_target()
        if not target:
            return None
        result = await (runTmuxInSwarm(["list-panes", "-t", target, "-F", "#{pane_id}"]) if useSwarmSocket else runTmuxInUserSession(["list-panes", "-t", target, "-F", "#{pane_id}"]))
        if result.get("code") != 0:
            return None
        return len([pane for pane in result.get("stdout", "").splitlines() if pane.strip()])

    async def _has_session_in_swarm(self, sessionName):
        result = await runTmuxInSwarm(["has-session", "-t", sessionName])
        return result.get("code") == 0

    async def _create_external_swarm_session(self):
        session_exists = await self._has_session_in_swarm(SWARM_SESSION_NAME)
        if not session_exists:
            result = await runTmuxInSwarm([
                "new-session",
                "-d",
                "-s",
                SWARM_SESSION_NAME,
                "-n",
                SWARM_VIEW_WINDOW_NAME,
                "-P",
                "-F",
                "#{pane_id}",
            ])
            if result.get("code") != 0:
                raise RuntimeError(f"Failed to create swarm session: {result.get('stderr', '')}")
            return {
                "windowTarget": f"{SWARM_SESSION_NAME}:{SWARM_VIEW_WINDOW_NAME}",
                "paneId": result.get("stdout", "").strip(),
            }

        window_target = f"{SWARM_SESSION_NAME}:{SWARM_VIEW_WINDOW_NAME}"
        list_result = await runTmuxInSwarm(["list-windows", "-t", SWARM_SESSION_NAME, "-F", "#{window_name}"])
        windows = [window for window in list_result.get("stdout", "").splitlines() if window.strip()]
        if SWARM_VIEW_WINDOW_NAME in windows:
            pane_result = await runTmuxInSwarm(["list-panes", "-t", window_target, "-F", "#{pane_id}"])
            panes = [pane for pane in pane_result.get("stdout", "").splitlines() if pane.strip()]
            return {"windowTarget": window_target, "paneId": panes[0] if panes else ""}

        create_result = await runTmuxInSwarm([
            "new-window",
            "-t",
            SWARM_SESSION_NAME,
            "-n",
            SWARM_VIEW_WINDOW_NAME,
            "-P",
            "-F",
            "#{pane_id}",
        ])
        if create_result.get("code") != 0:
            raise RuntimeError(f"Failed to create swarm-view window: {create_result.get('stderr', '')}")
        return {"windowTarget": window_target, "paneId": create_result.get("stdout", "").strip()}

    async def _create_teammate_pane_with_leader(self, teammateName, teammateColor):
        current_pane_id = await self._get_current_pane_id()
        window_target = await self._get_current_window_target()
        if not current_pane_id or not window_target:
            raise RuntimeError("Could not determine current tmux pane/window")

        pane_count = await self._get_current_window_pane_count(window_target)
        if pane_count is None:
            raise RuntimeError("Could not determine pane count for current window")

        is_first_teammate = pane_count == 1
        if is_first_teammate:
            split_result = await exec_file_no_throw(TMUX_COMMAND, ["split-window", "-t", current_pane_id, "-h", "-l", "70%", "-P", "-F", "#{pane_id}"])
        else:
            list_result = await exec_file_no_throw(TMUX_COMMAND, ["list-panes", "-t", window_target, "-F", "#{pane_id}"])
            panes = [pane for pane in list_result.get("stdout", "").splitlines() if pane.strip()]
            target_pane = panes[-1] if len(panes) > 1 else current_pane_id
            split_result = await exec_file_no_throw(TMUX_COMMAND, ["split-window", "-t", target_pane, "-v", "-P", "-F", "#{pane_id}"])

        if split_result.get("code") != 0:
            raise RuntimeError(f"Failed to create teammate pane: {split_result.get('stderr', '')}")

        pane_id = split_result.get("stdout", "").strip()
        await waitForPaneShellReady()
        await self.enablePaneBorderStatus(window_target)
        await self.setPaneBorderColor(pane_id, teammateColor)
        await self.setPaneTitle(pane_id, teammateName, teammateColor)
        await self.rebalancePanes(window_target, True)
        return {"paneId": pane_id, "isFirstTeammate": is_first_teammate}

    async def _create_teammate_pane_external(self, teammateName, teammateColor):
        global _first_pane_used_for_external
        created = await self._create_external_swarm_session()
        window_target = created["windowTarget"]

        if not _first_pane_used_for_external and created.get("paneId"):
            pane_id = created["paneId"]
            is_first_teammate = True
            _first_pane_used_for_external = True
        else:
            split_result = await runTmuxInSwarm(["split-window", "-t", window_target, "-v", "-P", "-F", "#{pane_id}"])
            if split_result.get("code") != 0:
                raise RuntimeError(f"Failed to create external teammate pane: {split_result.get('stderr', '')}")
            pane_id = split_result.get("stdout", "").strip()
            is_first_teammate = False

        await waitForPaneShellReady()
        await self.enablePaneBorderStatus(window_target, True)
        await self.setPaneBorderColor(pane_id, teammateColor, True)
        await self.setPaneTitle(pane_id, teammateName, teammateColor, True)
        await self.rebalancePanes(window_target, False)
        return {"paneId": pane_id, "isFirstTeammate": is_first_teammate}


registerTmuxBackend(TmuxBackend)
