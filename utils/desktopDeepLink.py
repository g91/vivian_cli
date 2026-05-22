"""Port of src/utils/desktopDeepLink.ts."""
from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import urlencode
import os
import os.path
import sys
import platform
import re


DesktopInstallStatus = Any
MIN_DESKTOP_VERSION = "1.1.2396"


def _coerce_version(version: str) -> Optional[str]:
    match = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", version or "")
    if not match:
        return None
    major = match.group(1) or "0"
    minor = match.group(2) or "0"
    patch = match.group(3) or "0"
    return f"{major}.{minor}.{patch}"


def isDevMode():
    if os.environ.get("NODE_ENV") == "development":
        return True

    paths_to_check = [sys.argv[0] if sys.argv else "", sys.executable or ""]
    build_dirs = [
        "/build-ant/",
        "/build-ant-native/",
        "/build-external/",
        "/build-external-native/",
    ]
    return any(build_dir in path for path in paths_to_check for build_dir in build_dirs)


def buildDesktopDeepLink(sessionId):
    """Builds a deep link URL for vivian Desktop to resume a CLI session."""
    from ..bootstrap.state import getSessionId
    from .cwd import get_cwd

    protocol = "vivian-dev" if isDevMode() else "vivian"
    effective_session_id = sessionId or getSessionId()
    query = urlencode({"session": effective_session_id, "cwd": get_cwd()})
    return f"{protocol}://resume?{query}"


async def isDesktopInstalled():
    """Check if vivian Desktop app is installed."""
    if isDevMode():
        return True

    current_platform = sys.platform
    if current_platform == "darwin":
        return os.path.exists("/Applications/vivian.app")
    if current_platform == "linux":
        from .execFileNoThrow import exec_file_no_throw

        result = await exec_file_no_throw(
            "xdg-mime",
            ["query", "default", "x-scheme-handler/vivian"],
        )
        return result.get("code") == 0 and bool(result.get("stdout", "").strip())
    if current_platform == "win32":
        from .execFileNoThrow import exec_file_no_throw

        result = await exec_file_no_throw(
            "reg",
            ["query", r"HKEY_CLASSES_ROOT\vivian", "/ve"],
        )
        return result.get("code") == 0
    return False


async def getDesktopVersion():
    """Detect the installed vivian Desktop version."""
    current_platform = sys.platform
    if current_platform == "darwin":
        from .execFileNoThrow import exec_file_no_throw

        result = await exec_file_no_throw(
            "defaults",
            [
                "read",
                "/Applications/vivian.app/Contents/Info.plist",
                "CFBundleShortVersionString",
            ],
        )
        if result.get("code") != 0:
            return None
        version = result.get("stdout", "").strip()
        return version or None

    if current_platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            return None
        install_dir = os.path.join(local_app_data, "Anthropicvivian")
        try:
            entries = os.listdir(install_dir)
        except Exception:
            return None
        versions = []
        for entry in entries:
            if not entry.startswith("app-"):
                continue
            version = entry[4:]
            coerced = _coerce_version(version)
            if coerced is not None:
                versions.append((coerced, version))
        versions.sort(key=lambda item: tuple(int(part) for part in item[0].split(".")))
        return versions[-1][1] if versions else None

    return None


async def getDesktopInstallStatus():
    """Check Desktop install status including version compatibility."""
    installed = await isDesktopInstalled()
    if not installed:
        return {"status": "not-installed"}

    try:
        version = await getDesktopVersion()
    except Exception:
        return {"status": "ready", "version": "unknown"}

    if not version:
        return {"status": "ready", "version": "unknown"}

    coerced = _coerce_version(version)
    if not coerced:
        return {"status": "ready", "version": "unknown"}

    from .semver import gte

    if not gte(coerced, MIN_DESKTOP_VERSION):
        return {"status": "version-too-old", "version": version}
    return {"status": "ready", "version": version}


async def openDeepLink(deepLinkUrl):
    """Opens a deep link URL using the platform-specific mechanism."""
    from .debug import log_for_debugging
    from .execFileNoThrow import exec_file_no_throw

    log_for_debugging(f"Opening deep link: {deepLinkUrl}")
    current_platform = sys.platform
    if current_platform == "darwin":
        if isDevMode():
            result = await exec_file_no_throw(
                "osascript",
                ["-e", f'tell application "Electron" to open location "{deepLinkUrl}"'],
            )
            return result.get("code") == 0
        result = await exec_file_no_throw("open", [deepLinkUrl])
        return result.get("code") == 0
    if current_platform == "linux":
        result = await exec_file_no_throw("xdg-open", [deepLinkUrl])
        return result.get("code") == 0
    if current_platform == "win32":
        result = await exec_file_no_throw("cmd", ["/c", "start", "", deepLinkUrl])
        return result.get("code") == 0
    return False


async def openCurrentSessionInDesktop():
    """Build and open a deep link to resume the current session in vivian Desktop."""
    from ..bootstrap.state import getSessionId

    session_id = getSessionId()
    installed = await isDesktopInstalled()
    if not installed:
        return {
            "success": False,
            "error": "vivian Desktop is not installed. Install it from https://api-vivian.d0a.net/download",
        }

    deep_link_url = buildDesktopDeepLink(session_id)
    opened = await openDeepLink(deep_link_url)
    if not opened:
        return {
            "success": False,
            "error": "Failed to open vivian Desktop. Please try opening it manually.",
            "deepLinkUrl": deep_link_url,
        }
    return {"success": True, "deepLinkUrl": deep_link_url}


is_dev_mode = isDevMode
build_desktop_deep_link = buildDesktopDeepLink
is_desktop_installed = isDesktopInstalled
get_desktop_version = getDesktopVersion
get_desktop_install_status = getDesktopInstallStatus
open_deep_link = openDeepLink
open_current_session_in_desktop = openCurrentSessionInDesktop

