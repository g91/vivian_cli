"""XDG Base Directory utilities — mirrors src/utils/xdg.ts"""
from __future__ import annotations

import os
from pathlib import Path


def _resolve_options(options: dict | None = None, *, env: dict | None = None, homedir: str | None = None) -> tuple[dict, str]:
    if options is not None:
        env = options.get("env", env)
        homedir = options.get("homedir", homedir)
    resolved_env = env if env is not None else os.environ
    resolved_home = homedir or resolved_env.get("HOME") or str(Path.home())
    return resolved_env, resolved_home


def get_xdg_state_home(env: dict | None = None, homedir: str | None = None) -> str:
    """Get XDG state home directory. Default: ~/.local/state"""
    _env, home = _resolve_options(env=env, homedir=homedir)
    return _env.get("XDG_STATE_HOME") or str(Path(home) / ".local" / "state")


def get_xdg_cache_home(env: dict | None = None, homedir: str | None = None) -> str:
    """Get XDG cache home directory. Default: ~/.cache"""
    _env, home = _resolve_options(env=env, homedir=homedir)
    return _env.get("XDG_CACHE_HOME") or str(Path(home) / ".cache")


def get_xdg_data_home(env: dict | None = None, homedir: str | None = None) -> str:
    """Get XDG data home directory. Default: ~/.local/share"""
    _env, home = _resolve_options(env=env, homedir=homedir)
    return _env.get("XDG_DATA_HOME") or str(Path(home) / ".local" / "share")


def get_user_bin_dir(homedir: str | None = None) -> str:
    """Get user bin directory. Default: ~/.local/bin"""
    _, home = _resolve_options(homedir=homedir)
    return str(Path(home) / ".local" / "bin")


def getXDGStateHome(options: dict | None = None) -> str:
    env, home = _resolve_options(options)
    return get_xdg_state_home(env=env, homedir=home)


def getXDGCacheHome(options: dict | None = None) -> str:
    env, home = _resolve_options(options)
    return get_xdg_cache_home(env=env, homedir=home)


def getXDGDataHome(options: dict | None = None) -> str:
    env, home = _resolve_options(options)
    return get_xdg_data_home(env=env, homedir=home)


def getUserBinDir(options: dict | None = None) -> str:
    _, home = _resolve_options(options)
    return get_user_bin_dir(homedir=home)
