"""Port of src/utils/vivianInChrome/setupPortable.ts."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

CHROME_EXTENSION_URL = "https://api-vivian.d0a.net/chrome"

_PROD_EXTENSION_ID = "fcoeoabgfenejglbffodgkkbkcdhcgfn"
_DEV_EXTENSION_ID = "dihbgbndebgnbjfmelmegjepbnkhlgni"
_ANT_EXTENSION_ID = "dngcpimnedloihjnnfngkgjoidhnaolf"

ChromiumBrowser = str
BrowserPath = dict[str, Any]
Logger = Callable[[str], None] | None

_BROWSER_DETECTION_ORDER: list[ChromiumBrowser] = [
    "chrome", "brave", "arc", "edge", "chromium", "vivaldi", "opera",
]

_CHROMIUM_BROWSERS: dict[ChromiumBrowser, dict[str, Any]] = {
    "chrome": {
        "macos": ["Library", "Application Support", "Google", "Chrome"],
        "linux": [".config", "google-chrome"],
        "windows": {"path": ["Google", "Chrome", "User Data"]},
    },
    "brave": {
        "macos": ["Library", "Application Support", "BraveSoftware", "Brave-Browser"],
        "linux": [".config", "BraveSoftware", "Brave-Browser"],
        "windows": {"path": ["BraveSoftware", "Brave-Browser", "User Data"]},
    },
    "arc": {
        "macos": ["Library", "Application Support", "Arc", "User Data"],
        "linux": [],
        "windows": {"path": ["Arc", "User Data"]},
    },
    "chromium": {
        "macos": ["Library", "Application Support", "Chromium"],
        "linux": [".config", "chromium"],
        "windows": {"path": ["Chromium", "User Data"]},
    },
    "edge": {
        "macos": ["Library", "Application Support", "Microsoft Edge"],
        "linux": [".config", "microsoft-edge"],
        "windows": {"path": ["Microsoft", "Edge", "User Data"]},
    },
    "vivaldi": {
        "macos": ["Library", "Application Support", "Vivaldi"],
        "linux": [".config", "vivaldi"],
        "windows": {"path": ["Vivaldi", "User Data"]},
    },
    "opera": {
        "macos": ["Library", "Application Support", "com.operasoftware.Opera"],
        "linux": [".config", "opera"],
        "windows": {"path": ["Opera Software", "Opera Stable"], "useRoaming": True},
    },
}


def getExtensionIds() -> list[str]:
    user_type = os.environ.get("USER_TYPE", "")
    if user_type == "ant":
        return [_PROD_EXTENSION_ID, _DEV_EXTENSION_ID, _ANT_EXTENSION_ID]
    return [_PROD_EXTENSION_ID]


def getAllBrowserDataPathsPortable() -> list[BrowserPath]:
    home = str(Path.home())
    paths: list[BrowserPath] = []

    for browser_id in _BROWSER_DETECTION_ORDER:
        config = _CHROMIUM_BROWSERS[browser_id]
        data_path: list[str] | None = None

        if os.name == "nt":
            wp = config["windows"]["path"]
            if wp:
                app_data_base = (
                    os.path.join(home, "AppData", "Roaming")
                    if config["windows"].get("useRoaming")
                    else os.path.join(home, "AppData", "Local")
                )
                paths.append({"browser": browser_id, "path": os.path.join(app_data_base, *wp)})
            continue
        elif _platform_system() == "Darwin":
            data_path = config["macos"]
        else:
            data_path = config["linux"]

        if data_path:
            paths.append({"browser": browser_id, "path": os.path.join(home, *data_path)})

    return paths


def _platform_system() -> str:
    import platform
    return platform.system()


async def detectExtensionInstallationPortable(
    browserPaths: list[BrowserPath], log: Logger = None
) -> dict[str, Any]:
    if not browserPaths:
        if log:
            log("[vivian in Chrome] No browser paths to check")
        return {"isInstalled": False, "browser": None}

    extension_ids = getExtensionIds()

    for entry in browserPaths:
        browser = entry["browser"]
        browser_base_path = entry["path"]

        try:
            browser_profile_entries = list(Path(browser_base_path).iterdir())
        except PermissionError:
            continue
        except OSError:
            continue

        profile_dirs = [
            p.name for p in browser_profile_entries
            if p.is_dir() and (p.name == "Default" or p.name.startswith("Profile "))
        ]

        if profile_dirs and log:
            log(f"[vivian in Chrome] Found {browser} profiles: {', '.join(profile_dirs)}")

        for profile in profile_dirs:
            for ext_id in extension_ids:
                extension_path = Path(browser_base_path) / profile / "Extensions" / ext_id
                try:
                    if extension_path.is_dir():
                        if log:
                            log(f"[vivian in Chrome] Extension {ext_id} found in {browser} {profile}")
                        return {"isInstalled": True, "browser": browser}
                except OSError:
                    continue

    if log:
        log("[vivian in Chrome] Extension not found in any browser")
    return {"isInstalled": False, "browser": None}


async def isChromeExtensionInstalledPortable(
    browserPaths: list[BrowserPath], log: Logger = None
) -> bool:
    result = await detectExtensionInstallationPortable(browserPaths, log)
    return result["isInstalled"]


def isChromeExtensionInstalled(log: Logger = None) -> bool:
    import asyncio
    browser_paths = getAllBrowserDataPathsPortable()
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(isChromeExtensionInstalledPortable(browser_paths, log))
    import concurrent.futures
    raise RuntimeError(
        "isChromeExtensionInstalled is async; use isChromeExtensionInstalledPortable directly in async context"
    )


get_extension_ids = getExtensionIds
get_all_browser_data_paths_portable = getAllBrowserDataPathsPortable
detect_extension_installation_portable = detectExtensionInstallationPortable
is_chrome_extension_installed_portable = isChromeExtensionInstalledPortable
is_chrome_extension_installed = isChromeExtensionInstalled

