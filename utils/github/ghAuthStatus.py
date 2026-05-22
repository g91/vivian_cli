"""gh CLI authentication status — mirrors src/utils/github/ghAuthStatus.ts"""
from __future__ import annotations

import shutil
import subprocess
from typing import Literal

GhAuthStatus = Literal["authenticated", "not_authenticated", "not_installed"]


async def get_gh_auth_status() -> GhAuthStatus:
    """Return gh CLI install + auth status.

    Uses ``shutil.which`` first (no subprocess) to detect install,
    then ``gh auth token`` exit-code to detect auth without making a
    network request.
    """
    gh_path = shutil.which("gh")
    if not gh_path:
        return "not_installed"

    try:
        result = subprocess.run(
            [gh_path, "auth", "token"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return "authenticated" if result.returncode == 0 else "not_authenticated"
    except (subprocess.TimeoutExpired, OSError):
        return "not_authenticated"
