"""advisor command — mirrors src/commands/advisor.ts.

Configure the advisor model for architectural guidance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..utils.advisor import is_valid_advisor_model, model_supports_advisor
from ..utils.model.model import getDefaultMainLoopModelSetting, parseUserSpecifiedModel
from ..utils.model.validateModel import validateModel
from ..utils.settings.settings import updateSettingsForSource

if TYPE_CHECKING:
    from ..types.command import CommandContext, TextResult


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


async def call(args: str, context: CommandContext) -> TextResult:
    """Configure or query the advisor model."""
    from ..types.command import TextResult

    arg = args.strip().lower() if args else ""

    app_state = _get_app_state(context)
    base_model = parseUserSpecifiedModel(
        app_state.get("mainLoopModel") or getDefaultMainLoopModelSetting()
    )
    current = app_state.get("advisorModel")
    if current is None:
        try:
            current = getattr(context, "config", {}).get("advisor_model")
        except Exception:
            current = None

    if not arg:
        if current:
            if not model_supports_advisor(base_model):
                return TextResult(
                    f"Advisor: {current} (inactive)\nThe current model ({base_model}) does not support advisors."
                )
            return TextResult(
                f'Advisor: {current}\nUse "/advisor unset" to disable or "/advisor <model>" to change.'
            )
        return TextResult('Advisor: not set\nUse /advisor <model> to enable (e.g. /advisor qwen3.6).')

    if arg in ("unset", "off"):
        if current is None:
            return TextResult("Advisor already unset.")

        merged_state = dict(app_state)
        merged_state["advisorModel"] = None
        _set_app_state(context, merged_state)
        try:
            if hasattr(context, "set_setting"):
                context.set_setting("advisor_model", None)
        except Exception:
            pass
        try:
            updateSettingsForSource("userSettings", {"advisorModel": None})
        except Exception:
            pass
        return TextResult(f"Advisor disabled (was {current}).")

    resolved_model = parseUserSpecifiedModel(arg)
    normalized_model = resolved_model
    validation = await validateModel(resolved_model)
    if not validation.get("valid"):
        error = validation.get("error")
        if error:
            return TextResult(f"Invalid advisor model: {error}")
        return TextResult(f"Unknown model: {arg} ({resolved_model})")

    if not is_valid_advisor_model(resolved_model):
        return TextResult(
            f"The model {arg} ({resolved_model}) cannot be used as an advisor"
        )

    merged_state = dict(app_state)
    merged_state["advisorModel"] = normalized_model
    _set_app_state(context, merged_state)
    try:
        if hasattr(context, "set_setting"):
            context.set_setting("advisor_model", normalized_model)
    except Exception:
        pass
    try:
        updateSettingsForSource("userSettings", {"advisorModel": normalized_model})
    except Exception:
        pass

    if not model_supports_advisor(base_model):
        return TextResult(
            f"Advisor set to {normalized_model}.\n"
            f"Note: Your current model ({base_model}) does not support advisors. Switch to a supported model to use the advisor."
        )

    return TextResult(f"Advisor set to {normalized_model}.")


advisorInfo = call
advisor_info = call
