"""Port of src/utils/swarm/backends/detection.ts."""
from __future__ import annotations

import os

from ...env import detectTerminal
from ...execFileNoThrow import exec_file_no_throw
from ..constants import TMUX_COMMAND


IT2_COMMAND = "it2"

_ORIGINAL_USER_TMUX = os.environ.get("TMUX")
_ORIGINAL_TMUX_PANE = os.environ.get("TMUX_PANE")
_is_inside_tmux_cached: bool | None = None
_is_in_iterm2_cached: bool | None = None


def isInsideTmuxSync() -> bool:
    return bool(_ORIGINAL_USER_TMUX)


async def isInsideTmux() -> bool:
    global _is_inside_tmux_cached
    if _is_inside_tmux_cached is not None:
        return _is_inside_tmux_cached
    _is_inside_tmux_cached = bool(_ORIGINAL_USER_TMUX)
    return _is_inside_tmux_cached


def getLeaderPaneId() -> str | None:
    return _ORIGINAL_TMUX_PANE or None


async def isTmuxAvailable() -> bool:
    result = await exec_file_no_throw(TMUX_COMMAND, ["-V"])
    return result.get("code") == 0


def isInITerm2() -> bool:
    global _is_in_iterm2_cached
    if _is_in_iterm2_cached is not None:
        return _is_in_iterm2_cached

    term_program = os.environ.get("TERM_PROGRAM")
    has_iterm_session_id = bool(os.environ.get("ITERM_SESSION_ID"))
    terminal_is_iterm = detectTerminal() == "iTerm.app"
    _is_in_iterm2_cached = (
        term_program == "iTerm.app" or has_iterm_session_id or terminal_is_iterm
    )
    return _is_in_iterm2_cached


async def isIt2CliAvailable() -> bool:
    result = await exec_file_no_throw(IT2_COMMAND, ["session", "list"])
    return result.get("code") == 0


def resetDetectionCache() -> None:
    global _is_inside_tmux_cached, _is_in_iterm2_cached
    _is_inside_tmux_cached = None
    _is_in_iterm2_cached = None


is_inside_tmux_sync = isInsideTmuxSync
is_inside_tmux = isInsideTmux
get_leader_pane_id = getLeaderPaneId
is_tmux_available = isTmuxAvailable
is_in_iterm2 = isInITerm2
is_it2_cli_available = isIt2CliAvailable
reset_detection_cache = resetDetectionCache