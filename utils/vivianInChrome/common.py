"""Port of src/utils/vivianInChrome/common.ts."""
from __future__ import annotations

import os
import platform as _platform
import asyncio
from pathlib import Path
from typing import Any

from ...services.mcp.normalization import normalizeNameForMCP
from ..debug import logForDebugging

vivian_IN_CHROME_MCP_SERVER_NAME = "vivian-in-chrome"

ChromiumBrowser = str

BrowserConfig = dict[str, Any]

CHROMIUM_BROWSERS: dict[ChromiumBrowser, BrowserConfig] = {
    "chrome": {
        "name": "Google Chrome",
        "macos": {
            "appName": "Google Chrome",
            "dataPath": ["Library", "Application Support", "Google", "Chrome"],
            "nativeMessagingPath": [
                "Library", "Application Support", "Google", "Chrome", "NativeMessagingHosts",
            ],
        },
        "linux": {
            "binaries": ["google-chrome", "google-chrome-stable"],
            "dataPath": [".config", "google-chrome"],
            "nativeMessagingPath": [".config", "google-chrome", "NativeMessagingHosts"],
        },
        "windows": {
            "dataPath": ["Google", "Chrome", "User Data"],
            "registryKey": "HKCU\\Software\\Google\\Chrome\\NativeMessagingHosts",
        },
    },
    "brave": {
        "name": "Brave",
        "macos": {
            "appName": "Brave Browser",
            "dataPath": ["Library", "Application Support", "BraveSoftware", "Brave-Browser"],
            "nativeMessagingPath": [
                "Library", "Application Support", "BraveSoftware", "Brave-Browser", "NativeMessagingHosts",
            ],
        },
        "linux": {
            "binaries": ["brave-browser", "brave"],
            "dataPath": [".config", "BraveSoftware", "Brave-Browser"],
            "nativeMessagingPath": [".config", "BraveSoftware", "Brave-Browser", "NativeMessagingHosts"],
        },
        "windows": {
            "dataPath": ["BraveSoftware", "Brave-Browser", "User Data"],
            "registryKey": "HKCU\\Software\\BraveSoftware\\Brave-Browser\\NativeMessagingHosts",
        },
    },
    "arc": {
        "name": "Arc",
        "macos": {
            "appName": "Arc",
            "dataPath": ["Library", "Application Support", "Arc", "User Data"],
            "nativeMessagingPath": [
                "Library", "Application Support", "Arc", "User Data", "NativeMessagingHosts",
            ],
        },
        "linux": {"binaries": [], "dataPath": [], "nativeMessagingPath": []},
        "windows": {
            "dataPath": ["Arc", "User Data"],
            "registryKey": "HKCU\\Software\\ArcBrowser\\Arc\\NativeMessagingHosts",
        },
    },
    "chromium": {
        "name": "Chromium",
        "macos": {
            "appName": "Chromium",
            "dataPath": ["Library", "Application Support", "Chromium"],
            "nativeMessagingPath": [
                "Library", "Application Support", "Chromium", "NativeMessagingHosts",
            ],
        },
        "linux": {
            "binaries": ["chromium", "chromium-browser"],
            "dataPath": [".config", "chromium"],
            "nativeMessagingPath": [".config", "chromium", "NativeMessagingHosts"],
        },
        "windows": {
            "dataPath": ["Chromium", "User Data"],
            "registryKey": "HKCU\\Software\\Chromium\\NativeMessagingHosts",
        },
    },
    "edge": {
        "name": "Microsoft Edge",
        "macos": {
            "appName": "Microsoft Edge",
            "dataPath": ["Library", "Application Support", "Microsoft Edge"],
            "nativeMessagingPath": [
                "Library", "Application Support", "Microsoft Edge", "NativeMessagingHosts",
            ],
        },
        "linux": {
            "binaries": ["microsoft-edge", "microsoft-edge-stable"],
            "dataPath": [".config", "microsoft-edge"],
            "nativeMessagingPath": [".config", "microsoft-edge", "NativeMessagingHosts"],
        },
        "windows": {
            "dataPath": ["Microsoft", "Edge", "User Data"],
            "registryKey": "HKCU\\Software\\Microsoft\\Edge\\NativeMessagingHosts",
        },
    },
    "vivaldi": {
        "name": "Vivaldi",
        "macos": {
            "appName": "Vivaldi",
            "dataPath": ["Library", "Application Support", "Vivaldi"],
            "nativeMessagingPath": [
                "Library", "Application Support", "Vivaldi", "NativeMessagingHosts",
            ],
        },
        "linux": {
            "binaries": ["vivaldi", "vivaldi-stable"],
            "dataPath": [".config", "vivaldi"],
            "nativeMessagingPath": [".config", "vivaldi", "NativeMessagingHosts"],
        },
        "windows": {
            "dataPath": ["Vivaldi", "User Data"],
            "registryKey": "HKCU\\Software\\Vivaldi\\NativeMessagingHosts",
        },
    },
    "opera": {
        "name": "Opera",
        "macos": {
            "appName": "Opera",
            "dataPath": ["Library", "Application Support", "com.operasoftware.Opera"],
            "nativeMessagingPath": [
                "Library", "Application Support", "com.operasoftware.Opera", "NativeMessagingHosts",
            ],
        },
        "linux": {
            "binaries": ["opera"],
            "dataPath": [".config", "opera"],
            "nativeMessagingPath": [".config", "opera", "NativeMessagingHosts"],
        },
        "windows": {
            "dataPath": ["Opera Software", "Opera Stable"],
            "registryKey": "HKCU\\Software\\Opera Software\\Opera Stable\\NativeMessagingHosts",
            "useRoaming": True,
        },
    },
}

BROWSER_DETECTION_ORDER: list[ChromiumBrowser] = [
    "chrome", "brave", "arc", "edge", "chromium", "vivaldi", "opera",
]


def _get_platform() -> str:
    system = _platform.system()
    if system == "Darwin":
        return "macos"
    if system == "Windows":
        return "windows"
    return "linux"


def getAllBrowserDataPaths() -> list[dict[str, Any]]:
    plat = _get_platform()
    home = str(Path.home())
    paths: list[dict[str, Any]] = []

    for browser_id in BROWSER_DETECTION_ORDER:
        config = CHROMIUM_BROWSERS[browser_id]
        data_path: list[str] | None = None

        if plat == "macos":
            data_path = config["macos"]["dataPath"]
        elif plat in ("linux", "wsl"):
            data_path = config["linux"]["dataPath"]
        elif plat == "windows":
            wp = config["windows"]["dataPath"]
            if wp:
                app_data_base = (
                    os.path.join(home, "AppData", "Roaming")
                    if config["windows"].get("useRoaming")
                    else os.path.join(home, "AppData", "Local")
                )
                paths.append({"browser": browser_id, "path": os.path.join(app_data_base, *wp)})
            continue

        if data_path:
            paths.append({"browser": browser_id, "path": os.path.join(home, *data_path)})

    return paths


def getAllNativeMessagingHostsDirs() -> list[dict[str, Any]]:
    plat = _get_platform()
    home = str(Path.home())
    paths: list[dict[str, Any]] = []

    for browser_id in BROWSER_DETECTION_ORDER:
        config = CHROMIUM_BROWSERS[browser_id]

        if plat == "macos":
            nmp = config["macos"]["nativeMessagingPath"]
            if nmp:
                paths.append({"browser": browser_id, "path": os.path.join(home, *nmp)})
        elif plat in ("linux", "wsl"):
            nmp = config["linux"]["nativeMessagingPath"]
            if nmp:
                paths.append({"browser": browser_id, "path": os.path.join(home, *nmp)})

    return paths


def getAllWindowsRegistryKeys() -> list[dict[str, Any]]:
    keys: list[dict[str, Any]] = []
    for browser_id in BROWSER_DETECTION_ORDER:
        config = CHROMIUM_BROWSERS[browser_id]
        rk = config["windows"].get("registryKey")
        if rk:
            keys.append({"browser": browser_id, "key": rk})
    return keys


async def detectAvailableBrowser() -> ChromiumBrowser | None:
    plat = _get_platform()

    for browser_id in BROWSER_DETECTION_ORDER:
        config = CHROMIUM_BROWSERS[browser_id]

        if plat == "macos":
            app_path = f"/Applications/{config['macos']['appName']}.app"
            if Path(app_path).is_dir():
                return browser_id
        elif plat in ("linux", "wsl"):
            for binary in config["linux"]["binaries"]:
                proc = await asyncio.create_subprocess_exec(
                    "which", binary,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                code = await proc.wait()
                if code == 0:
                    return browser_id
        elif plat == "windows":
            home = str(Path.home())
            wp = config["windows"]["dataPath"]
            if wp:
                app_data_base = (
                    os.path.join(home, "AppData", "Roaming")
                    if config["windows"].get("useRoaming")
                    else os.path.join(home, "AppData", "Local")
                )
                if Path(os.path.join(app_data_base, *wp)).is_dir():
                    return browser_id

    return None


def isvivianInChromeMCPServer(name: str) -> bool:
    return normalizeNameForMCP(name) == vivian_IN_CHROME_MCP_SERVER_NAME


MAX_TRACKED_TABS = 200
_tracked_tab_ids: set[int] = set()


def trackvivianInChromeTabId(tabId: int) -> None:
    if len(_tracked_tab_ids) >= MAX_TRACKED_TABS and tabId not in _tracked_tab_ids:
        _tracked_tab_ids.clear()
    _tracked_tab_ids.add(tabId)


def isTrackedvivianInChromeTabId(tabId: int) -> bool:
    return tabId in _tracked_tab_ids


async def openInChrome(url: str) -> bool:
    plat = _get_platform()
    browser = await detectAvailableBrowser()

    if not browser:
        logForDebugging("[vivian in Chrome] No compatible browser found")
        return False

    config = CHROMIUM_BROWSERS[browser]

    if plat == "macos":
        proc = await asyncio.create_subprocess_exec(
            "open", "-a", config["macos"]["appName"], url,
        )
        return (await proc.wait()) == 0
    elif plat == "windows":
        proc = await asyncio.create_subprocess_exec("rundll32", "url,OpenURL", url)
        return (await proc.wait()) == 0
    elif plat in ("linux", "wsl"):
        for binary in config["linux"]["binaries"]:
            proc = await asyncio.create_subprocess_exec(binary, url)
            if (await proc.wait()) == 0:
                return True
        return False
    return False


def _get_username() -> str:
    try:
        import pwd
        return pwd.getpwuid(os.getuid()).pw_name or "default"
    except Exception:
        return os.environ.get("USER") or os.environ.get("USERNAME") or "default"


def getSocketDir() -> str:
    return f"/tmp/vivian-mcp-browser-bridge-{_get_username()}"


def getSecureSocketPath() -> str:
    if _platform.system() == "Windows":
        return f"\\\\.\\pipe\\{_get_socket_name()}"
    return os.path.join(getSocketDir(), f"{os.getpid()}.sock")


def getAllSocketPaths() -> list[str]:
    if _platform.system() == "Windows":
        return [f"\\\\.\\pipe\\{_get_socket_name()}"]

    paths: list[str] = []
    socket_dir = getSocketDir()

    try:
        for entry in os.scandir(socket_dir):
            if entry.name.endswith(".sock"):
                paths.append(entry.path)
    except OSError:
        pass

    legacy_name = f"vivian-mcp-browser-bridge-{_get_username()}"
    legacy_tmpdir = os.path.join("/tmp", legacy_name)
    legacy_tmp = f"/tmp/{legacy_name}"

    if legacy_tmpdir not in paths:
        paths.append(legacy_tmpdir)
    if legacy_tmpdir != legacy_tmp and legacy_tmp not in paths:
        paths.append(legacy_tmp)

    return paths


def _get_socket_name() -> str:
    return f"vivian-mcp-browser-bridge-{_get_username()}"


get_all_browser_data_paths = getAllBrowserDataPaths
get_all_native_messaging_hosts_dirs = getAllNativeMessagingHostsDirs
get_all_windows_registry_keys = getAllWindowsRegistryKeys
detect_available_browser = detectAvailableBrowser
is_vivian_in_chrome_mcp_server = isvivianInChromeMCPServer
track_vivian_in_chrome_tab_id = trackvivianInChromeTabId
is_tracked_vivian_in_chrome_tab_id = isTrackedvivianInChromeTabId
open_in_chrome = openInChrome
get_socket_dir = getSocketDir
get_secure_socket_path = getSecureSocketPath
get_all_socket_paths = getAllSocketPaths

