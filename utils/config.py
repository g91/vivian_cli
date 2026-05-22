"""Global configuration — mirrors src/utils/config.ts"""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

_global_config: dict = {}

def get_global_config() -> dict:
    return _global_config

def save_global_config(config: dict | Callable[[dict], dict]) -> None:
    global _global_config
    if callable(config):
        _global_config = config(dict(_global_config))
    else:
        _global_config = config

def get_or_create_user_id() -> str:
    import uuid
    uid_key = "user_id"
    if uid_key in _global_config:
        return _global_config[uid_key]
    new_id = str(uuid.uuid4())
    _global_config[uid_key] = new_id
    return new_id


def enableConfigs() -> None:
    """Initialize config system for this process (in-memory for now)."""
    # Touch global config to ensure module-level state is ready.
    _ = _global_config


def enable_configs() -> None:
    enableConfigs()


def recordFirstStartTime() -> None:
    """Record the first startup timestamp in ms if it has not been set."""
    key = "firstStartTime"
    if key not in _global_config:
        _global_config[key] = int(time.time() * 1000)


def record_first_start_time() -> None:
    recordFirstStartTime()


def getGlobalConfig() -> dict:
    return get_global_config()


def saveGlobalConfig(config: dict | Callable[[dict], dict]) -> None:
    save_global_config(config)


def getOrCreateUserId() -> str:
    return get_or_create_user_id()


def shouldSkipPluginAutoupdate() -> bool:
    return bool(_global_config.get("skipPluginAutoupdate", False))
