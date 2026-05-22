"""Port of src/utils/hooks/hooksConfigSnapshot.ts"""
from __future__ import annotations
from typing import Any, Optional, Dict

_initial_hooks_config: Optional[Dict[str, Any]] = None


def _get_settings_for_source(source: str) -> Optional[Dict[str, Any]]:
    try:
        from vivian_cli.utils.settings.settings import get_settings_for_source
        return get_settings_for_source(source)
    except ImportError:
        return None


def _get_merged_settings() -> Dict[str, Any]:
    try:
        from vivian_cli.utils.settings.settings import get_settings
        return get_settings()
    except ImportError:
        return {}


def _get_hooks_from_allowed_sources() -> Dict[str, Any]:
    """Get hooks from allowed sources, respecting policy restrictions."""
    policy = _get_settings_for_source('policySettings') or {}

    if policy.get('disableAllHooks') is True:
        return {}

    if policy.get('allowManagedHooksOnly') is True:
        return policy.get('hooks', {})

    merged = _get_merged_settings()

    if merged.get('disableAllHooks') is True:
        return policy.get('hooks', {})

    return merged.get('hooks', {})


def should_allow_managed_hooks_only() -> bool:
    """True when only managed hooks should run."""
    policy = _get_settings_for_source('policySettings') or {}
    if policy.get('allowManagedHooksOnly') is True:
        return True
    merged = _get_merged_settings()
    if merged.get('disableAllHooks') is True and policy.get('disableAllHooks') is not True:
        return True
    return False


shouldAllowManagedHooksOnly = should_allow_managed_hooks_only


def should_disable_all_hooks_including_managed() -> bool:
    """True only when policy settings has disableAllHooks: true."""
    policy = _get_settings_for_source('policySettings') or {}
    return policy.get('disableAllHooks') is True


shouldDisableAllHooksIncludingManaged = should_disable_all_hooks_including_managed


def capture_hooks_config_snapshot() -> None:
    """Capture a snapshot of the current hooks configuration."""
    global _initial_hooks_config
    _initial_hooks_config = _get_hooks_from_allowed_sources()


captureHooksConfigSnapshot = capture_hooks_config_snapshot


def update_hooks_config_snapshot() -> None:
    """Update the hooks configuration snapshot (e.g. after user edits settings)."""
    global _initial_hooks_config
    try:
        from vivian_cli.utils.settings.settingsCache import reset_settings_cache
        reset_settings_cache()
    except ImportError:
        pass
    _initial_hooks_config = _get_hooks_from_allowed_sources()


updateHooksConfigSnapshot = update_hooks_config_snapshot


def get_hooks_config_from_snapshot() -> Optional[Dict[str, Any]]:
    """Get hooks config from snapshot, capturing it first if not yet done."""
    global _initial_hooks_config
    if _initial_hooks_config is None:
        capture_hooks_config_snapshot()
    return _initial_hooks_config


getHooksConfigFromSnapshot = get_hooks_config_from_snapshot


def reset_hooks_config_snapshot() -> None:
    """Reset the hooks config snapshot (for testing)."""
    global _initial_hooks_config
    _initial_hooks_config = None


resetHooksConfigSnapshot = reset_hooks_config_snapshot

