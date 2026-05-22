"""brief command — mirrors src/commands/brief.ts.

Toggle brief-only mode where AI output is condensed.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ..bootstrap.state import getKairosActive, setUserMsgOptIn
from ..services.analytics.growthbook import getFeatureValue_CACHED_MAY_BE_STALE
from ..services.analytics.index import log_event
from ..tools.BriefTool.prompt import BRIEF_TOOL_NAME

if TYPE_CHECKING:
    from ..types.command import CommandContext, TextResult


DEFAULT_BRIEF_CONFIG = {"enable_slash_command": False}


def _get_brief_config() -> dict:
    raw = getFeatureValue_CACHED_MAY_BE_STALE(
        "tengu_kairos_brief_config",
        DEFAULT_BRIEF_CONFIG,
    )
    if isinstance(raw, dict) and isinstance(raw.get("enable_slash_command"), bool):
        return raw
    return dict(DEFAULT_BRIEF_CONFIG)


def is_brief_slash_command_enabled() -> bool:
    if os.environ.get("KAIROS") or os.environ.get("KAIROS_BRIEF"):
        return _get_brief_config().get("enable_slash_command", False)
    return False


def _is_brief_entitled() -> bool:
    if getKairosActive():
        return True
    if os.environ.get("vivian_CODE_BRIEF"):
        return True
    return bool(getFeatureValue_CACHED_MAY_BE_STALE("tengu_kairos_brief", False))


def _get_app_state(context: CommandContext) -> dict:
    try:
        if hasattr(context, "get_app_state"):
            state = context.get_app_state()
            if isinstance(state, dict):
                return state
        if hasattr(context, "getAppState"):
            state = context.getAppState()
            if isinstance(state, dict):
                return state
    except Exception:
        pass
    return {}


def _set_app_state(context: CommandContext, new_state: dict) -> None:
    try:
        if hasattr(context, "set_app_state"):
            context.set_app_state(lambda _prev: new_state)
            return
        if hasattr(context, "setAppState"):
            context.setAppState(lambda _prev: new_state)
    except Exception:
        pass


def briefMode(enabled: bool) -> str:
    return "Brief-only mode enabled" if enabled else "Brief-only mode disabled"


async def call(args: str, context: CommandContext) -> TextResult:
    from ..types.command import TextResult

    current = False
    app_state = _get_app_state(context)
    try:
        current = bool(app_state.get("isBriefOnly", getattr(context, "config", {}).get("brief_mode", False)))
    except Exception:
        pass

    new_state = not current

    if new_state and not _is_brief_entitled():
        log_event(
            "tengu_brief_mode_toggled",
            {"enabled": False, "gated": True, "source": "slash_command"},
        )
        return TextResult("Brief tool is not enabled for your account")

    setUserMsgOptIn(new_state)

    merged_state = dict(app_state)
    merged_state["isBriefOnly"] = new_state
    _set_app_state(context, merged_state)

    try:
        if hasattr(context, "set_setting"):
            context.set_setting("brief_mode", new_state)
    except Exception:
        pass

    log_event(
        "tengu_brief_mode_toggled",
        {"enabled": new_state, "gated": False, "source": "slash_command"},
    )

    if getKairosActive():
        return TextResult(briefMode(new_state))

    reminder = (
        f"Use the {BRIEF_TOOL_NAME} tool for all user-facing output. Plain text outside it is hidden from the user's view."
        if new_state
        else f"The {BRIEF_TOOL_NAME} tool is no longer available. Reply with plain text."
    )
    return TextResult(f"{briefMode(new_state)}\n\n{reminder}")


brief_mode = briefMode
