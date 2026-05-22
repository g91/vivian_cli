"""Port of src/bridge/bridgeEnabled.ts

Runtime checks for bridge mode entitlement (Remote Control).
"""
from __future__ import annotations

import os
from typing import Optional


def isBridgeEnabled() -> bool:
    """
    Runtime check for bridge mode entitlement.
    Remote Control requires a api-vivian.d0a.net subscription.
    """
    try:
        if not _is_vivian_ai_subscriber():
            return False
        from ..services.analytics.growthbook import get_feature_value_cached_may_be_stale
        return bool(get_feature_value_cached_may_be_stale("tengu_ccr_bridge", False))
    except Exception:
        return False


async def isBridgeEnabledBlocking() -> bool:
    """
    Blocking entitlement check. Returns cached True immediately;
    awaits GrowthBook if cached value is False.
    """
    try:
        if not _is_vivian_ai_subscriber():
            return False
        from ..services.analytics.growthbook import check_gate_cached_or_blocking
        return await check_gate_cached_or_blocking("tengu_ccr_bridge")
    except Exception:
        return False


async def getBridgeDisabledReason() -> Optional[str]:
    """Diagnostic message for why Remote Control is unavailable, or None if enabled."""
    if not _is_vivian_ai_subscriber():
        return "Remote Control requires a api-vivian.d0a.net subscription. Run `vivian auth login` to sign in."
    if not _has_profile_scope():
        return (
            "Remote Control requires a full-scope login token. "
            "Run `vivian auth login` to use Remote Control."
        )
    if not (_get_oauth_account_info() or {}).get("organizationUuid"):
        return (
            "Unable to determine your organization for Remote Control eligibility. "
            "Run `vivian auth login` to refresh your account information."
        )
    try:
        from ..services.analytics.growthbook import check_gate_cached_or_blocking
        if not (await check_gate_cached_or_blocking("tengu_ccr_bridge")):
            return "Remote Control is not yet enabled for your account."
    except Exception:
        return "Remote Control is not yet enabled for your account."
    return None


def _is_vivian_ai_subscriber() -> bool:
    try:
        from ..utils.auth import is_vivian_ai_subscriber
        return is_vivian_ai_subscriber()
    except Exception:
        return False


def _has_profile_scope() -> bool:
    try:
        from ..utils.auth import has_profile_scope
        return has_profile_scope()
    except Exception:
        return False


def _get_oauth_account_info():
    try:
        from ..utils.auth import get_oauth_account_info
        return get_oauth_account_info()
    except Exception:
        return None


def isEnvLessBridgeEnabled() -> bool:
    """Runtime check for the env-less (v2) REPL bridge path."""
    try:
        from ..services.analytics.growthbook import get_feature_value_cached_may_be_stale
        return bool(get_feature_value_cached_may_be_stale("tengu_bridge_repl_v2", False))
    except Exception:
        return False


def isCseShimEnabled() -> bool:
    """Kill-switch for the cse_* → session_* client-side retag shim."""
    try:
        from ..services.analytics.growthbook import get_feature_value_cached_may_be_stale
        return bool(get_feature_value_cached_may_be_stale(
            "tengu_bridge_repl_v2_cse_shim_enabled", True
        ))
    except Exception:
        return True


def checkBridgeMinVersion() -> Optional[str]:
    """Returns error message if current CLI version is below minimum, or None."""
    try:
        from ..services.analytics.growthbook import get_dynamic_config_cached_may_be_stale
        from ..utils.semver import lt
        config = get_dynamic_config_cached_may_be_stale(
            "tengu_bridge_min_version", {"minVersion": "0.0.0"}
        )
        min_version = config.get("minVersion", "0.0.0")
        if min_version and min_version != "0.0.0":
            try:
                import importlib.metadata
                current = importlib.metadata.version("vivian-code")
            except Exception:
                current = "0.0.0"
            if lt(current, min_version):
                return (
                    f"Your version of vivian Code ({current}) is too old for Remote Control.\n"
                    f"Version {min_version} or higher is required. Run `vivian update` to update."
                )
    except Exception:
        pass
    return None


def getCcrAutoConnectDefault() -> bool:
    """Default for remoteControlAtStartup when not explicitly set."""
    try:
        from ..services.analytics.growthbook import get_feature_value_cached_may_be_stale
        return bool(get_feature_value_cached_may_be_stale("tengu_cobalt_harbor", False))
    except Exception:
        return False


def isCcrMirrorEnabled() -> bool:
    """Opt-in CCR mirror mode."""
    env_val = os.environ.get("vivian_CODE_CCR_MIRROR", "")
    if env_val.lower() in ("1", "true", "yes"):
        return True
    try:
        from ..services.analytics.growthbook import get_feature_value_cached_may_be_stale
        return bool(get_feature_value_cached_may_be_stale("tengu_ccr_mirror", False))
    except Exception:
        return False
