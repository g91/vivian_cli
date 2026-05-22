"""effort command — mirrors src/commands/effort/effort.tsx.

Set the effort/thinking level for the current session.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


HELP_TEXT = (
    "Usage: /effort [low|medium|high|max|auto]\n\n"
    "Effort levels:\n"
    "- low: Quick, straightforward implementation\n"
    "- medium: Balanced approach with standard testing\n"
    "- high: Comprehensive implementation with extensive testing\n"
    "- max: Maximum capability with deepest reasoning (Opus 4.6 only)\n"
    "- auto: Use the default effort level for your model"
)


def _get_current_model(context: CommandContext) -> str:
    try:
        query_engine = getattr(context, "query_engine", None)
        if query_engine is not None and getattr(query_engine, "model", None):
            return str(query_engine.model)
    except Exception:
        pass

    return str(getattr(context, "model", "") or "")


def _get_current_effort_value(context: CommandContext):
    try:
        state_store = getattr(context, "state_store", None)
        if state_store is not None and hasattr(state_store, "get_state"):
            return state_store.get_state().get("effortValue")

        app_state = getattr(context, "app_state", None)
        if app_state is not None:
            return app_state.get("effortValue")
    except Exception:
        pass

    return None


def _set_runtime_effort_value(context: CommandContext, value) -> None:
    try:
        state_store = getattr(context, "state_store", None)
        if state_store is not None and hasattr(state_store, "set_state"):
            state_store.set_state(lambda current: {**current, "effortValue": value})
            return
    except Exception:
        pass


def _persist_effort_setting(value) -> None:
    from ...utils.effort import toPersistableEffort
    from ...utils.settings.settings import getSettingsForSource, updateSettingsForSource

    persistable = toPersistableEffort(value)
    settings = dict(getSettingsForSource("userSettings") or {})

    if persistable is None:
        settings.pop("effortLevel", None)
    else:
        settings["effortLevel"] = persistable

    updateSettingsForSource("userSettings", settings)


def setEffort(level: str) -> str:
    from ...utils.effort import getEffortValueDescription

    if level == "auto":
        return "Effort level set to auto"
    return f"Set effort level to {level}: {getEffortValueDescription(level)}"


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    from ...utils.effort import getDisplayedEffortLevel, getEffortEnvOverride, getEffortValueDescription, isEffortLevel

    level = args.strip().lower() if args else ""

    if level in {"help", "-h", "--help"}:
        return TextResult(HELP_TEXT)

    if not level or level in {"current", "status"}:
        model = _get_current_model(context)
        current_value = _get_current_effort_value(context)
        env_override = getEffortEnvOverride()
        effective_value = env_override if env_override is not None else current_value
        if effective_value is None:
            return TextResult(f"Effort level: auto (currently {getDisplayedEffortLevel(model, current_value)})")
        return TextResult(f"Current effort level: {effective_value} ({getEffortValueDescription(effective_value)})")

    if level in {"auto", "unset"}:
        _set_runtime_effort_value(context, None)
        _persist_effort_setting(None)
        return TextResult("Effort level set to auto")

    if not isEffortLevel(level):
        return TextResult(f"Invalid argument: {level}. Valid options are: low, medium, high, max, auto")

    _set_runtime_effort_value(context, level)
    _persist_effort_setting(level)
    return TextResult(setEffort(level))


set_effort = setEffort
