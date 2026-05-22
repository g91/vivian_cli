"""Prompt suggestion service — mirrors src/services/PromptSuggestion/promptSuggestion.ts."""
from __future__ import annotations

import os
from typing import Literal, Optional

_current_abort_token = 0


def _env_value(name: str) -> Optional[str]:
    value = os.environ.get(name)
    return value.strip() if isinstance(value, str) else None


def _is_env_truthy(value: Optional[str]) -> bool:
    return value is not None and value.lower() not in ("", "0", "false", "no")


def _is_env_defined_falsy(value: Optional[str]) -> bool:
    return value is not None and value.lower() in ("0", "false", "no")

PromptVariant = Literal["user_intent", "stated_intent"]


def getPromptVariant() -> PromptVariant:
    """Get the current prompt variant.

    Mirrors getPromptVariant() from promptSuggestion.ts.
    """
    return "user_intent"


def shouldEnablePromptSuggestion() -> bool:
    """Check if prompt suggestion should be enabled.

    Mirrors shouldEnablePromptSuggestion() from promptSuggestion.ts.
    """
    env_override = _env_value("vivian_CODE_ENABLE_PROMPT_SUGGESTION")
    if _is_env_defined_falsy(env_override):
        return False
    if _is_env_truthy(env_override):
        return True

    try:
        from ...services.analytics.growthbook import getFeatureValue_CACHED_MAY_BE_STALE

        if not bool(getFeatureValue_CACHED_MAY_BE_STALE("tengu_chomp_inflection", False)):
            return False
    except Exception:
        return False

    try:
        from ...bootstrap.state import getIsNonInteractiveSession

        if getIsNonInteractiveSession():
            return False
    except Exception:
        return False

    try:
        from ...utils.settings.settings import getMergedSettings

        settings = getMergedSettings()
        return settings.get("promptSuggestionEnabled", True) is not False
    except Exception:
        return True


def abortPromptSuggestion() -> None:
    """Abort the current prompt suggestion.

    Mirrors abortPromptSuggestion() from promptSuggestion.ts.
    """
    global _current_abort_token
    _current_abort_token += 1


def getSuggestionSuppressReason(app_state: dict) -> Optional[str]:
    """Get the reason why prompt suggestion is suppressed.

    Mirrors getSuggestionSuppressReason() from promptSuggestion.ts.
    """
    if not app_state.get("promptSuggestionEnabled", False):
        return "disabled"
    if app_state.get("pendingWorkerRequest") or app_state.get("pendingSandboxRequest"):
        return "pending_permission"
    if (app_state.get("elicitation") or {}).get("queue"):
        return "elicitation_active"
    if (app_state.get("toolPermissionContext") or {}).get("mode") == "plan":
        return "plan_mode"
    return None


get_prompt_variant = getPromptVariant
should_enable_prompt_suggestion = shouldEnablePromptSuggestion
abort_prompt_suggestion = abortPromptSuggestion
get_suggestion_suppress_reason = getSuggestionSuppressReason
