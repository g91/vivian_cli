"""Port of src/bridge/envLessBridgeConfig.ts

Env-less (v2) REPL bridge timing config from GrowthBook.
"""
from __future__ import annotations

from typing import TypedDict


class EnvLessBridgeConfig(TypedDict):
    init_retry_max_attempts: int
    init_retry_base_delay_ms: int
    init_retry_jitter_fraction: float
    init_retry_max_delay_ms: int
    http_timeout_ms: int
    uuid_dedup_buffer_size: int
    heartbeat_interval_ms: int
    heartbeat_jitter_fraction: float
    token_refresh_buffer_ms: int
    teardown_archive_timeout_ms: int
    connect_timeout_ms: int
    min_version: str
    should_show_app_upgrade_message: bool


DEFAULT_ENV_LESS_BRIDGE_CONFIG: EnvLessBridgeConfig = {
    "init_retry_max_attempts": 3,
    "init_retry_base_delay_ms": 500,
    "init_retry_jitter_fraction": 0.25,
    "init_retry_max_delay_ms": 4000,
    "http_timeout_ms": 10_000,
    "uuid_dedup_buffer_size": 2000,
    "heartbeat_interval_ms": 20_000,
    "heartbeat_jitter_fraction": 0.1,
    "token_refresh_buffer_ms": 300_000,
    "teardown_archive_timeout_ms": 1500,
    "connect_timeout_ms": 15_000,
    "min_version": "0.0.0",
    "should_show_app_upgrade_message": False,
}


def _validate_env_less_config(raw: dict) -> EnvLessBridgeConfig:
    """Validate raw config dict. Returns default on any violation."""
    try:
        cfg = dict(DEFAULT_ENV_LESS_BRIDGE_CONFIG)
        cfg.update({k: v for k, v in raw.items() if k in DEFAULT_ENV_LESS_BRIDGE_CONFIG})

        checks = [
            1 <= cfg["init_retry_max_attempts"] <= 10,
            cfg["init_retry_base_delay_ms"] >= 100,
            0 <= cfg["init_retry_jitter_fraction"] <= 1,
            cfg["init_retry_max_delay_ms"] >= 500,
            cfg["http_timeout_ms"] >= 2000,
            100 <= cfg["uuid_dedup_buffer_size"] <= 50_000,
            5000 <= cfg["heartbeat_interval_ms"] <= 30_000,
            0 <= cfg["heartbeat_jitter_fraction"] <= 0.5,
            30_000 <= cfg["token_refresh_buffer_ms"] <= 1_800_000,
            500 <= cfg["teardown_archive_timeout_ms"] <= 2000,
            5_000 <= cfg["connect_timeout_ms"] <= 60_000,
            isinstance(cfg["min_version"], str),
        ]
        if not all(checks):
            return DEFAULT_ENV_LESS_BRIDGE_CONFIG
        return cfg  # type: ignore[return-value]
    except Exception:
        return DEFAULT_ENV_LESS_BRIDGE_CONFIG


async def getEnvLessBridgeConfig() -> EnvLessBridgeConfig:
    """Fetch the env-less bridge timing config from GrowthBook."""
    try:
        from ..services.analytics.growthbook import get_feature_value_deprecated
        raw = await get_feature_value_deprecated(
            "tengu_bridge_repl_v2_config",
            DEFAULT_ENV_LESS_BRIDGE_CONFIG,
        )
        if not isinstance(raw, dict):
            return DEFAULT_ENV_LESS_BRIDGE_CONFIG
        return _validate_env_less_config(raw)
    except Exception:
        return DEFAULT_ENV_LESS_BRIDGE_CONFIG


async def checkEnvLessBridgeMinVersion() -> str | None:
    """
    Returns an error message if current version is below minimum required for
    the env-less (v2) bridge path, or None if version is fine.
    """
    cfg = await getEnvLessBridgeConfig()
    min_version = cfg.get("min_version", "0.0.0")
    if min_version and min_version != "0.0.0":
        try:
            from ..utils.semver import lt
            import importlib.metadata
            try:
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


async def shouldShowAppUpgradeMessage() -> bool:
    """Whether to nudge users toward upgrading their api-vivian.d0a.net app."""
    try:
        from .bridgeEnabled import isEnvLessBridgeEnabled
        if not isEnvLessBridgeEnabled():
            return False
    except Exception:
        return False
    cfg = await getEnvLessBridgeConfig()
    return bool(cfg.get("should_show_app_upgrade_message", False))
