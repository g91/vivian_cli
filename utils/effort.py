"""Port of src/utils/effort.ts"""
from __future__ import annotations

import os
from typing import Any, Literal

from ..services.analytics.growthbook import getFeatureValue_CACHED_MAY_BE_STALE
from .auth import get_subscription_type, is_vivian_ai_subscriber
from .envUtils import is_env_truthy
from .model.antModels import getAntModelOverrideConfig, resolveAntModel
from .model.modelSupportOverrides import get3PModelCapabilityOverride
from .model.providers import getAPIProvider
from .thinking import is_ultrathink_enabled


EffortLevel = Literal["low", "medium", "high", "max"]
EffortValue = EffortLevel | int
OpusDefaultEffortConfig = dict[str, Any]

EFFORT_LEVELS: tuple[EffortLevel, ...] = ("low", "medium", "high", "max")

_OPUS_DEFAULT_EFFORT_CONFIG_DEFAULT: OpusDefaultEffortConfig = {
    "enabled": True,
    "dialogTitle": "We recommend medium effort for Opus",
    "dialogDescription": (
        "Effort determines how long vivian thinks for when completing your task. "
        "We recommend medium effort for most tasks to balance speed and intelligence "
        "and maximize rate limits. Use ultrathink to trigger high effort when needed."
    ),
}


def _get_initial_settings() -> dict[str, Any]:
    try:
        from .settings.settings import getInitialSettings  # type: ignore

        settings = getInitialSettings()
        return settings if isinstance(settings, dict) else dict(settings or {})
    except Exception:
        try:
            from .settings.settings import getMergedSettings

            settings = getMergedSettings()
            return settings if isinstance(settings, dict) else dict(settings or {})
        except Exception:
            return {}


def _subscription_type() -> str | None:
    try:
        return get_subscription_type()
    except Exception:
        return None


def _is_pro_subscriber() -> bool:
    return _subscription_type() == "pro"


def _is_max_subscriber() -> bool:
    return _subscription_type() == "max"


def _is_team_subscriber() -> bool:
    return _subscription_type() in {"team", "enterprise"}


def modelSupportsEffort(model: str) -> bool:
    m = model.lower()
    if is_env_truthy(os.environ.get("vivian_CODE_ALWAYS_ENABLE_EFFORT")):
        return True
    supported_3p = get3PModelCapabilityOverride(model, "effort")
    if supported_3p is not None:
        return supported_3p
    if "opus-4-6" in m or "sonnet-4-6" in m:
        return True
    if "haiku" in m or "sonnet" in m or "opus" in m:
        return False
    return getAPIProvider() == "firstParty"


def modelSupportsMaxEffort(model: str) -> bool:
    supported_3p = get3PModelCapabilityOverride(model, "max_effort")
    if supported_3p is not None:
        return supported_3p
    if "opus-4-6" in model.lower():
        return True
    if os.environ.get("USER_TYPE") == "ant" and resolveAntModel(model):
        return True
    return False


def isEffortLevel(value: str) -> bool:
    return value in EFFORT_LEVELS


def isValidNumericEffort(value: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def parseEffortValue(value: Any) -> EffortValue | None:
    if value in (None, ""):
        return None
    if isinstance(value, int) and isValidNumericEffort(value):
        return value
    str_value = str(value).lower()
    if isEffortLevel(str_value):
        return str_value
    try:
        numeric_value = int(str_value, 10)
    except ValueError:
        return None
    return numeric_value if isValidNumericEffort(numeric_value) else None


def toPersistableEffort(value: EffortValue | None) -> EffortLevel | None:
    if value in {"low", "medium", "high"}:
        return value
    if value == "max" and os.environ.get("USER_TYPE") == "ant":
        return value
    return None


def getInitialEffortSetting() -> EffortLevel | None:
    return toPersistableEffort(_get_initial_settings().get("effortLevel"))


def resolvePickerEffortPersistence(
    picked: EffortLevel | None,
    modelDefault: EffortLevel,
    priorPersisted: EffortLevel | None,
    toggledInPicker: bool,
) -> EffortLevel | None:
    had_explicit = priorPersisted is not None or toggledInPicker
    return picked if had_explicit or picked != modelDefault else None


def getEffortEnvOverride() -> EffortValue | None:
    env_override = os.environ.get("vivian_CODE_EFFORT_LEVEL")
    if env_override is None:
        return None
    lowered = env_override.lower()
    if lowered in {"unset", "auto"}:
        return None
    return parseEffortValue(env_override)


def resolveAppliedEffort(model: str, appStateEffortValue: EffortValue | None) -> EffortValue | None:
    env_override = getEffortEnvOverride()
    if os.environ.get("vivian_CODE_EFFORT_LEVEL", "").lower() in {"unset", "auto"}:
        return None
    resolved = env_override if env_override is not None else appStateEffortValue
    if resolved is None:
        resolved = getDefaultEffortForModel(model)
    if resolved == "max" and not modelSupportsMaxEffort(model):
        return "high"
    return resolved


def convertEffortValueToLevel(value: EffortValue) -> EffortLevel:
    if isinstance(value, str):
        return value if isEffortLevel(value) else "high"
    if os.environ.get("USER_TYPE") == "ant":
        if value <= 50:
            return "low"
        if value <= 85:
            return "medium"
        if value <= 100:
            return "high"
        return "max"
    return "high"


def getDisplayedEffortLevel(model: str, appStateEffort: EffortValue | None) -> EffortLevel:
    resolved = resolveAppliedEffort(model, appStateEffort) or "high"
    return convertEffortValueToLevel(resolved)


def getEffortSuffix(model: str, effortValue: EffortValue | None) -> str:
    if effortValue is None:
        return ""
    resolved = resolveAppliedEffort(model, effortValue)
    if resolved is None:
        return ""
    return f" with {convertEffortValueToLevel(resolved)} effort"


def getEffortLevelDescription(level: EffortLevel) -> str:
    if level == "low":
        return "Quick, straightforward implementation with minimal overhead"
    if level == "medium":
        return "Balanced approach with standard implementation and testing"
    if level == "high":
        return "Comprehensive implementation with extensive testing and documentation"
    return "Maximum capability with deepest reasoning (Opus 4.6 only)"


def getEffortValueDescription(value: EffortValue) -> str:
    if os.environ.get("USER_TYPE") == "ant" and isinstance(value, int):
        return f"[ANT-ONLY] Numeric effort value of {value}"
    if isinstance(value, str):
        return getEffortLevelDescription(value)
    return "Balanced approach with standard implementation and testing"


def getOpusDefaultEffortConfig() -> OpusDefaultEffortConfig:
    config = getFeatureValue_CACHED_MAY_BE_STALE(
        "tengu_grey_step2",
        _OPUS_DEFAULT_EFFORT_CONFIG_DEFAULT,
    )
    if not isinstance(config, dict):
        config = {}
    return {
        **_OPUS_DEFAULT_EFFORT_CONFIG_DEFAULT,
        **config,
    }


def getDefaultEffortForModel(model: str) -> EffortValue | None:
    lower_model = model.lower()
    if os.environ.get("USER_TYPE") == "ant":
        config = getAntModelOverrideConfig()
        default_model = config.get("defaultModel") if isinstance(config, dict) else None
        is_default_model = isinstance(default_model, str) and lower_model == default_model.lower()
        if is_default_model and isinstance(config, dict) and config.get("defaultModelEffortLevel"):
            return config["defaultModelEffortLevel"]
        ant_model = resolveAntModel(model)
        if ant_model:
            if getattr(ant_model, "defaultEffortLevel", None):
                return ant_model.defaultEffortLevel
            if getattr(ant_model, "defaultEffortValue", None) is not None:
                return ant_model.defaultEffortValue
        return None

    if "opus-4-6" in lower_model:
        if _is_pro_subscriber():
            return "medium"
        if getOpusDefaultEffortConfig().get("enabled") and (_is_max_subscriber() or _is_team_subscriber()):
            return "medium"

    if is_ultrathink_enabled() and modelSupportsEffort(model):
        return "medium"

    return None


model_supports_effort = modelSupportsEffort
model_supports_max_effort = modelSupportsMaxEffort
is_effort_level = isEffortLevel
parse_effort_value = parseEffortValue
to_persistable_effort = toPersistableEffort
get_initial_effort_setting = getInitialEffortSetting
resolve_picker_effort_persistence = resolvePickerEffortPersistence
get_effort_env_override = getEffortEnvOverride
resolve_applied_effort = resolveAppliedEffort
get_displayed_effort_level = getDisplayedEffortLevel
get_effort_suffix = getEffortSuffix
is_valid_numeric_effort = isValidNumericEffort
convert_effort_value_to_level = convertEffortValueToLevel
get_effort_level_description = getEffortLevelDescription
get_effort_value_description = getEffortValueDescription
get_opus_default_effort_config = getOpusDefaultEffortConfig
get_default_effort_for_model = getDefaultEffortForModel

