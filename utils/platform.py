"""Platform detection — mirrors src/utils/platform.ts"""
from __future__ import annotations

import os
import platform
import sys
from functools import lru_cache
from typing import Literal, Optional

Platform = Literal["macos", "windows", "wsl", "linux", "unknown"]

SUPPORTED_PLATFORMS: list[str] = ["macos", "wsl"]


@lru_cache(maxsize=1)
def get_platform() -> Platform:
    """Detect the current platform. Cached after first call."""
    try:
        if sys.platform == "darwin":
            return "macos"
        if sys.platform == "win32":
            return "windows"
        if sys.platform.startswith("linux"):
            try:
                proc_version = open("/proc/version").read()
                if "microsoft" in proc_version.lower() or "wsl" in proc_version.lower():
                    return "wsl"
            except OSError:
                pass
            return "linux"
        return "unknown"
    except Exception:
        return "unknown"


@lru_cache(maxsize=1)
def get_wsl_version() -> Optional[str]:
    """Return WSL version string if running under WSL, else None."""
    if sys.platform != "linux":
        return None
    try:
        proc_version = open("/proc/version").read()
        import re
        match = re.search(r"WSL(\d+)", proc_version, re.IGNORECASE)
        if match:
            return match.group(1)
        if "microsoft" in proc_version.lower():
            return "1"
        return None
    except Exception:
        return None


class LinuxDistroInfo:
    def __init__(
        self,
        linux_distro_id: Optional[str] = None,
        linux_distro_version: Optional[str] = None,
        linux_kernel: Optional[str] = None,
    ) -> None:
        self.linux_distro_id = linux_distro_id
        self.linux_distro_version = linux_distro_version
        self.linux_kernel = linux_kernel


def get_linux_distro_info() -> Optional[LinuxDistroInfo]:
    """Return Linux distro info (ID, version, kernel). None on non-Linux."""
    if sys.platform != "linux":
        return None
    import platform as _platform
    result = LinuxDistroInfo(linux_kernel=_platform.release())
    try:
        import re
        content = open("/etc/os-release").read()
        for line in content.split("\n"):
            match = re.match(r"^(ID|VERSION_ID)=(.*)$", line)
            if match:
                value = match.group(2).strip('"')
                if match.group(1) == "ID":
                    result.linux_distro_id = value
                else:
                    result.linux_distro_version = value
    except OSError:
        pass
    return result


_VCS_MARKERS = [
    (".git", "git"),
    (".hg", "mercurial"),
    (".svn", "svn"),
    (".p4config", "perforce"),
    ("$tf", "tfs"),
    (".tfvc", "tfs"),
    (".jj", "jujutsu"),
    (".sl", "sapling"),
]


def detect_vcs(directory: Optional[str] = None) -> list[str]:
    """Detect version control systems in the given directory."""
    detected: set[str] = set()
    if os.environ.get("P4PORT"):
        detected.add("perforce")
    try:
        target_dir = directory or os.getcwd()
        entries = set(os.listdir(target_dir))
        for marker, vcs in _VCS_MARKERS:
            if marker in entries:
                detected.add(vcs)
    except OSError:
        pass
    return list(detected)
