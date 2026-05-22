"""Port of src/utils/computerUse/gates.ts."""
from __future__ import annotations

import os

from ...services.analytics.growthbook import getDynamicConfig_CACHED_MAY_BE_STALE
from ..auth import get_subscription_type
from ..envUtils import is_env_truthy


DEFAULTS = {
    "enabled": False,
    "pixelValidation": False,
    "clipboardPasteMultiline": True,
    "mouseAnimation": True,
    "hideBeforeAction": True,
    "autoTargetDisplay": True,
    "clipboardGuard": True,
    "coordinateMode": "pixels",
}
_frozen_coordinate_mode = None


def readConfig():
    config = getDynamicConfig_CACHED_MAY_BE_STALE("tengu_malort_pedway", DEFAULTS)
    if not isinstance(config, dict):
        return dict(DEFAULTS)
    return {**DEFAULTS, **config}


def hasRequiredSubscription():
    if os.environ.get("USER_TYPE", "") == "ant":
        return True
    tier = get_subscription_type()
    return tier in {"max", "pro"}


def getChicagoEnabled():
    if (
        os.environ.get("USER_TYPE", "") == "ant"
        and os.environ.get("MONOREPO_ROOT_DIR", "")
        and not is_env_truthy(os.environ.get("ALLOW_ANT_COMPUTER_USE_MCP", ""))
    ):
        return False
    return hasRequiredSubscription() and bool(readConfig()["enabled"])


def getChicagoSubGates():
    config = dict(readConfig())
    config.pop("enabled", None)
    config.pop("coordinateMode", None)
    return config


def getChicagoCoordinateMode():
    global _frozen_coordinate_mode
    if _frozen_coordinate_mode is None:
        _frozen_coordinate_mode = readConfig()["coordinateMode"]
    return _frozen_coordinate_mode


read_config = readConfig
has_required_subscription = hasRequiredSubscription
get_chicago_enabled = getChicagoEnabled
get_chicago_sub_gates = getChicagoSubGates
get_chicago_coordinate_mode = getChicagoCoordinateMode

