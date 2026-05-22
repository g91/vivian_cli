"""Port of src/utils/swarm/backends/teammateModeSnapshot.ts."""
from __future__ import annotations

from ...config import get_global_config
from ...debug import logForDebugging
from ...log import logError


TeammateMode = str

_initial_teammate_mode: TeammateMode | None = None
_cli_teammate_mode_override: TeammateMode | None = None


def setCliTeammateModeOverride(mode: TeammateMode) -> None:
    global _cli_teammate_mode_override
    _cli_teammate_mode_override = mode


def getCliTeammateModeOverride() -> TeammateMode | None:
    return _cli_teammate_mode_override


def clearCliTeammateModeOverride(newMode: TeammateMode) -> None:
    global _cli_teammate_mode_override, _initial_teammate_mode
    _cli_teammate_mode_override = None
    _initial_teammate_mode = newMode
    logForDebugging(
        f"[TeammateModeSnapshot] CLI override cleared, new mode: {newMode}"
    )


def captureTeammateModeSnapshot() -> None:
    global _initial_teammate_mode
    if _cli_teammate_mode_override:
        _initial_teammate_mode = _cli_teammate_mode_override
        logForDebugging(
            f"[TeammateModeSnapshot] Captured from CLI override: {_initial_teammate_mode}"
        )
        return

    config = get_global_config() or {}
    _initial_teammate_mode = config.get("teammateMode") or "auto"
    logForDebugging(
        f"[TeammateModeSnapshot] Captured from config: {_initial_teammate_mode}"
    )


def getTeammateModeFromSnapshot() -> TeammateMode:
    global _initial_teammate_mode
    if _initial_teammate_mode is None:
        logError(
            RuntimeError(
                "getTeammateModeFromSnapshot called before capture - this indicates an initialization bug"
            )
        )
        captureTeammateModeSnapshot()
    return _initial_teammate_mode or "auto"


set_cli_teammate_mode_override = setCliTeammateModeOverride
get_cli_teammate_mode_override = getCliTeammateModeOverride
clear_cli_teammate_mode_override = clearCliTeammateModeOverride
capture_teammate_mode_snapshot = captureTeammateModeSnapshot
get_teammate_mode_from_snapshot = getTeammateModeFromSnapshot