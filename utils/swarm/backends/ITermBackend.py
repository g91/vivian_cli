"""Port of src/utils/swarm/backends/ITermBackend.ts."""
from __future__ import annotations

import asyncio
import os
import re

from ...debug import logForDebugging
from ...execFileNoThrow import exec_file_no_throw
from .detection import IT2_COMMAND, isInITerm2, isIt2CliAvailable
from .registry import registerITermBackend


_teammate_session_ids: list[str] = []
_first_pane_used = False
_pane_creation_lock = asyncio.Lock()


async def acquirePaneCreationLock():
    await _pane_creation_lock.acquire()

    def _release() -> None:
        if _pane_creation_lock.locked():
            _pane_creation_lock.release()

    return _release


async def runIt2(args):
    return await exec_file_no_throw(IT2_COMMAND, args)


def parseSplitOutput(output):
    match = re.search(r"Created new pane:\s*(.+)", output or "")
    return match.group(1).strip() if match else ""


def getLeaderSessionId():
    iterm_session_id = os.environ.get("ITERM_SESSION_ID")
    if not iterm_session_id or ":" not in iterm_session_id:
        return None
    return iterm_session_id.split(":", 1)[1]


class ITermBackend:
    def __init__(self):
        self.type = "iterm2"
        self.displayName = "iTerm2"
        self.supportsHideShow = False

    async def isAvailable(self):
        in_iterm2 = isInITerm2()
        logForDebugging(f"[ITermBackend] isAvailable check: inITerm2={in_iterm2}")
        if not in_iterm2:
            return False
        available = await isIt2CliAvailable()
        logForDebugging(f"[ITermBackend] isAvailable: {available}")
        return available

    async def isRunningInside(self):
        result = isInITerm2()
        logForDebugging(f"[ITermBackend] isRunningInside: {result}")
        return result

    async def createTeammatePaneInSwarmView(self, name, color):
        del color
        global _first_pane_used
        release_lock = await acquirePaneCreationLock()
        try:
            while True:
                is_first_teammate = not _first_pane_used
                targeted_teammate_id = None
                if is_first_teammate:
                    leader_session_id = getLeaderSessionId()
                    split_args = ["session", "split", "-v", "-s", leader_session_id] if leader_session_id else ["session", "split", "-v"]
                else:
                    targeted_teammate_id = _teammate_session_ids[-1] if _teammate_session_ids else None
                    split_args = ["session", "split", "-s", targeted_teammate_id] if targeted_teammate_id else ["session", "split"]

                split_result = await runIt2(split_args)
                if split_result.get("code") != 0:
                    if targeted_teammate_id:
                        list_result = await runIt2(["session", "list"])
                        if list_result.get("code") == 0 and targeted_teammate_id not in str(list_result.get("stdout", "")):
                            logForDebugging(
                                f"[ITermBackend] Split failed targeting dead session {targeted_teammate_id}, pruning and retrying"
                            )
                            try:
                                _teammate_session_ids.remove(targeted_teammate_id)
                            except ValueError:
                                pass
                            if not _teammate_session_ids:
                                _first_pane_used = False
                            continue
                    raise RuntimeError(
                        f"Failed to create iTerm2 split pane: {split_result.get('stderr', '')}"
                    )

                if is_first_teammate:
                    _first_pane_used = True

                pane_id = parseSplitOutput(split_result.get("stdout", ""))
                if not pane_id:
                    raise RuntimeError(
                        f"Failed to parse session ID from split output: {split_result.get('stdout', '')}"
                    )
                _teammate_session_ids.append(pane_id)
                logForDebugging(f"[ITermBackend] Created teammate pane for {name}: {pane_id}")
                return {"paneId": pane_id, "isFirstTeammate": is_first_teammate}
        finally:
            release_lock()

    async def sendCommandToPane(self, paneId, command, _useExternalSession=None):
        args = ["session", "run", "-s", paneId, command] if paneId else ["session", "run", command]
        result = await runIt2(args)
        if result.get("code") != 0:
            raise RuntimeError(
                f"Failed to send command to iTerm2 pane {paneId}: {result.get('stderr', '')}"
            )

    async def setPaneBorderColor(self, _paneId, _color, _useExternalSession=None):
        return None

    async def setPaneTitle(self, _paneId, _name, _color, _useExternalSession=None):
        return None

    async def enablePaneBorderStatus(self, _windowTarget=None, _useExternalSession=None):
        return None

    async def rebalancePanes(self, _windowTarget, _hasLeader):
        logForDebugging("[ITermBackend] Pane rebalancing not implemented for iTerm2")

    async def killPane(self, paneId, _useExternalSession=None):
        global _first_pane_used
        result = await runIt2(["session", "close", "-f", "-s", paneId])
        try:
            _teammate_session_ids.remove(paneId)
        except ValueError:
            pass
        if not _teammate_session_ids:
            _first_pane_used = False
        return result.get("code") == 0

    async def hidePane(self, _paneId, _useExternalSession=None):
        logForDebugging("[ITermBackend] hidePane not supported in iTerm2")
        return False

    async def showPane(self, _paneId, _targetWindowOrPane, _useExternalSession=None):
        logForDebugging("[ITermBackend] showPane not supported in iTerm2")
        return False


registerITermBackend(ITermBackend)