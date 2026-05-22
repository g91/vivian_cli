"""color command — mirrors src/commands/color/color.ts.

Set the current session agent color.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult

AGENT_COLORS = ["cyan", "yellow", "magenta", "green", "blue", "red"]
RESET_ALIASES = {"default", "reset", "none", "gray", "grey"}


def _set_session_color(context: CommandContext, color: str | None) -> None:
    try:
        state_store = getattr(context, "state_store", None)
        if state_store is not None and hasattr(state_store, "set_state"):
            state_store.set_state(
                lambda current: {
                    **current,
                    "standaloneAgentContext": {
                        **(current.get("standaloneAgentContext") or {}),
                        "name": ((current.get("standaloneAgentContext") or {}).get("name") or ""),
                        "color": color,
                    },
                }
            )
    except Exception:
        pass


def _save_session_color(color: str) -> None:
    from ...bootstrap.state import getSessionId
    from ...utils.sessionStorage import appendSessionEntry, getTranscriptPath

    appendSessionEntry(
        {
            "type": "agent-color",
            "sessionId": getSessionId(),
            "agentColor": color,
        },
        getTranscriptPath(),
    )


def setColorScheme(scheme: str) -> str:
    """Set the session color."""
    if scheme in AGENT_COLORS:
        return f"Session color set to: {scheme}"
    if scheme in RESET_ALIASES:
        return "Session color reset to default"
    return f"Invalid color \"{scheme}\". Available colors: {', '.join(AGENT_COLORS)}, default"


async def call(args: str, context: CommandContext) -> TextResult:
    """View or change the session color."""
    from ...types.command import TextResult

    scheme = args.strip().lower() if args else ""

    if not scheme:
        return TextResult(f"Please provide a color. Available colors: {', '.join(AGENT_COLORS)}, default")

    if scheme in RESET_ALIASES:
        _save_session_color("default")
        _set_session_color(context, None)
        return TextResult("Session color reset to default")

    if scheme not in AGENT_COLORS:
        return TextResult(setColorScheme(scheme))

    try:
        _save_session_color(scheme)
        _set_session_color(context, scheme)
    except Exception:
        pass

    return TextResult(setColorScheme(scheme))


set_color_scheme = setColorScheme
