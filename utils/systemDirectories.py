"""System directories — mirrors src/utils/systemDirectories.ts"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .platform import get_platform, Platform


class SystemDirectories(dict):
    """Dict subclass holding system directory paths."""


def get_system_directories(
    *,
    env: dict | None = None,
    homedir: str | None = None,
    platform: Platform | None = None,
) -> SystemDirectories:
    """Return cross-platform system directory paths.

    Mirrors getSystemDirectories() from systemDirectories.ts.
    """
    _platform = platform or get_platform()
    _home = homedir or str(Path.home())
    _env = env if env is not None else os.environ

    defaults = SystemDirectories(
        HOME=_home,
        DESKTOP=str(Path(_home) / "Desktop"),
        DOCUMENTS=str(Path(_home) / "Documents"),
        DOWNLOADS=str(Path(_home) / "Downloads"),
    )

    if _platform == "windows":
        user_profile = _env.get("USERPROFILE") or _home
        return SystemDirectories(
            HOME=_home,
            DESKTOP=str(Path(user_profile) / "Desktop"),
            DOCUMENTS=str(Path(user_profile) / "Documents"),
            DOWNLOADS=str(Path(user_profile) / "Downloads"),
        )

    if _platform in ("linux", "wsl"):
        return SystemDirectories(
            HOME=_home,
            DESKTOP=_env.get("XDG_DESKTOP_DIR") or defaults["DESKTOP"],
            DOCUMENTS=_env.get("XDG_DOCUMENTS_DIR") or defaults["DOCUMENTS"],
            DOWNLOADS=_env.get("XDG_DOWNLOAD_DIR") or defaults["DOWNLOADS"],
        )

    # macOS and unknown
    return defaults
