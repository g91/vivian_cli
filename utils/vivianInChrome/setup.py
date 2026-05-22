"""Port of src/utils/vivianInChrome/setup.ts."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from ...bootstrap.state import (
    getIsInteractive,
    getIsNonInteractiveSession,
    getSessionBypassPermissionsMode,
)
from ...services.analytics.growthbook import getFeatureValue_CACHED_MAY_BE_STALE
from ...services.mcp.mcpStringUtils import buildMcpToolName
from ..bundledMode import is_in_bundled_mode
from ..config import get_global_config, save_global_config
from ..debug import logForDebugging
from ..envUtils import is_env_truthy, is_env_defined_falsy, get_vivian_config_home_dir
from .common import (
    vivian_IN_CHROME_MCP_SERVER_NAME,
    getAllBrowserDataPaths,
    getAllNativeMessagingHostsDirs,
    getAllWindowsRegistryKeys,
    openInChrome,
)
from .prompt import getChromeSystemPrompt
from .setupPortable import isChromeExtensionInstalledPortable, getAllBrowserDataPathsPortable

CHROME_EXTENSION_RECONNECT_URL = "https://api-vivian.d0a.net/chrome/reconnect"
NATIVE_HOST_IDENTIFIER = "com.anthropic.vivian_code_browser_extension"
NATIVE_HOST_MANIFEST_NAME = f"{NATIVE_HOST_IDENTIFIER}.json"

_should_auto_enable: bool | None = None


def shouldEnablevivianInChrome(chromeFlag: bool | None = None) -> bool:
    if getIsNonInteractiveSession() and chromeFlag is not True:
        return False
    if chromeFlag is True:
        return True
    if chromeFlag is False:
        return False
    if is_env_truthy(os.environ.get("vivian_CODE_ENABLE_CFC", "")):
        return True
    if is_env_defined_falsy(os.environ.get("vivian_CODE_ENABLE_CFC", "")):
        return False
    config = get_global_config()
    if config.get("vivianInChromeDefaultEnabled") is not None:
        return config["vivianInChromeDefaultEnabled"]
    return False


def shouldAutoEnablevivianInChrome() -> bool:
    global _should_auto_enable
    if _should_auto_enable is not None:
        return _should_auto_enable

    _should_auto_enable = (
        getIsInteractive()
        and _isChromeExtensionInstalledCachedMayBeStale()
        and (
            os.environ.get("USER_TYPE") == "ant"
            or getFeatureValue_CACHED_MAY_BE_STALE("tengu_chrome_auto_enable", False)
        )
    )
    return _should_auto_enable


def setupvivianInChrome() -> dict[str, Any]:
    is_native_build = is_in_bundled_mode()

    # Build allowed tools list from known browser tool names
    _BROWSER_TOOL_NAMES = [
        "javascript_tool", "read_page", "find", "form_input", "computer",
        "navigate", "resize_window", "gif_creator", "upload_image",
        "get_page_text", "tabs_context_mcp", "tabs_create_mcp", "update_plan",
        "read_console_messages", "read_network_requests", "shortcuts_list",
        "shortcuts_execute",
    ]
    allowed_tools = [
        buildMcpToolName(vivian_IN_CHROME_MCP_SERVER_NAME, name)
        for name in _BROWSER_TOOL_NAMES
    ]

    env: dict[str, str] = {}
    if getSessionBypassPermissionsMode():
        env["vivian_CHROME_PERMISSION_MODE"] = "skip_all_permission_checks"
    has_env = len(env) > 0

    if is_native_build:
        exec_command = f'"{sys.executable}" --chrome-native-host'
        asyncio.ensure_future(_install_native_host_async(exec_command))

        mcp_config = {
            vivian_IN_CHROME_MCP_SERVER_NAME: {
                "type": "stdio",
                "command": sys.executable,
                "args": ["--vivian-in-chrome-mcp"],
                "scope": "dynamic",
                **({"env": env} if has_env else {}),
            }
        }
    else:
        cli_path = str(Path(__file__).resolve().parent.parent.parent / "cli.js")
        exec_command = f'"{sys.executable}" "{cli_path}" --chrome-native-host'
        asyncio.ensure_future(_install_native_host_async(exec_command))

        mcp_config = {
            vivian_IN_CHROME_MCP_SERVER_NAME: {
                "type": "stdio",
                "command": sys.executable,
                "args": [cli_path, "--vivian-in-chrome-mcp"],
                "scope": "dynamic",
                **({"env": env} if has_env else {}),
            }
        }

    return {
        "mcpConfig": mcp_config,
        "allowedTools": allowed_tools,
        "systemPrompt": getChromeSystemPrompt(),
    }


async def _install_native_host_async(exec_command: str) -> None:
    try:
        manifest_binary_path = await createWrapperScript(exec_command)
        await installChromeNativeHostManifest(manifest_binary_path)
    except Exception as e:
        logForDebugging(f"[vivian in Chrome] Failed to install native host: {e}", level="error")


def getNativeMessagingHostsDirs() -> list[str]:
    plat = _get_platform()
    if plat == "windows":
        home = str(Path.home())
        app_data = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Local")
        return [os.path.join(app_data, "vivian Code", "ChromeNativeHost")]
    return [entry["path"] for entry in getAllNativeMessagingHostsDirs()]


async def installChromeNativeHostManifest(manifestBinaryPath: str) -> None:
    manifest_dirs = getNativeMessagingHostsDirs()
    if not manifest_dirs:
        raise RuntimeError("vivian in Chrome Native Host not supported on this platform")

    allowed_origins = [
        "chrome-extension://fcoeoabgfenejglbffodgkkbkcdhcgfn/",
    ]
    if os.environ.get("USER_TYPE") == "ant":
        allowed_origins.extend([
            "chrome-extension://dihbgbndebgnbjfmelmegjepbnkhlgni/",
            "chrome-extension://dngcpimnedloihjnnfngkgjoidhnaolf/",
        ])

    manifest = {
        "name": NATIVE_HOST_IDENTIFIER,
        "description": "vivian Code Browser Extension Native Host",
        "path": manifestBinaryPath,
        "type": "stdio",
        "allowed_origins": allowed_origins,
    }

    manifest_content = json.dumps(manifest, indent=2)
    any_manifest_updated = False

    for manifest_dir in manifest_dirs:
        manifest_path = os.path.join(manifest_dir, NATIVE_HOST_MANIFEST_NAME)

        try:
            existing = Path(manifest_path).read_text(encoding="utf-8")
        except Exception:
            existing = None

        if existing == manifest_content:
            continue

        try:
            Path(manifest_dir).mkdir(parents=True, exist_ok=True)
            Path(manifest_path).write_text(manifest_content, encoding="utf-8")
            logForDebugging(f"[vivian in Chrome] Installed native host manifest at: {manifest_path}")
            any_manifest_updated = True
        except Exception as error:
            logForDebugging(f"[vivian in Chrome] Failed to install manifest at {manifest_path}: {error}")

    if _get_platform() == "windows":
        manifest_path = os.path.join(manifest_dirs[0], NATIVE_HOST_MANIFEST_NAME)
        registerWindowsNativeHosts(manifest_path)

    if any_manifest_updated:
        asyncio.ensure_future(_reconnect_if_installed())


async def _reconnect_if_installed() -> None:
    try:
        browser_paths = getAllBrowserDataPathsPortable()
        is_installed = await isChromeExtensionInstalledPortable(browser_paths)
        if is_installed:
            logForDebugging("[vivian in Chrome] First-time install detected, opening reconnect page in browser")
            await openInChrome(CHROME_EXTENSION_RECONNECT_URL)
        else:
            logForDebugging("[vivian in Chrome] First-time install detected, but extension not installed, skipping reconnect")
    except Exception:
        pass


def registerWindowsNativeHosts(manifestPath: str) -> None:
    registry_keys = getAllWindowsRegistryKeys()
    for entry in registry_keys:
        browser = entry["browser"]
        key = entry["key"]
        full_key = f"{key}\\{NATIVE_HOST_IDENTIFIER}"
        asyncio.ensure_future(_reg_add(full_key, manifest_path, browser))


async def _reg_add(full_key: str, manifest_path: str, browser: str) -> None:
    try:
        proc = await asyncio.create_subprocess_exec(
            "reg", "add", full_key, "/ve", "/t", "REG_SZ", "/d", manifest_path, "/f",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            logForDebugging(f"[vivian in Chrome] Registered native host for {browser} in Windows registry: {full_key}")
        else:
            logForDebugging(f"[vivian in Chrome] Failed to register native host for {browser}: {stderr.decode() if stderr else ''}")
    except Exception:
        pass


async def createWrapperScript(command: str) -> str:
    plat = _get_platform()
    chrome_dir = os.path.join(get_vivian_config_home_dir(), "chrome")
    wrapper_path = (
        os.path.join(chrome_dir, "chrome-native-host.bat")
        if plat == "windows"
        else os.path.join(chrome_dir, "chrome-native-host")
    )

    if plat == "windows":
        script_content = f'@echo off\nREM Chrome native host wrapper script\nREM Generated by vivian Code - do not edit manually\n{command}\n'
    else:
        script_content = f'#!/bin/sh\n# Chrome native host wrapper script\n# Generated by vivian Code - do not edit manually\nexec {command}\n'

    try:
        existing = Path(wrapper_path).read_text(encoding="utf-8")
    except Exception:
        existing = None

    if existing == script_content:
        return wrapper_path

    Path(chrome_dir).mkdir(parents=True, exist_ok=True)
    Path(wrapper_path).write_text(script_content, encoding="utf-8")

    if plat != "windows":
        os.chmod(wrapper_path, 0o755)

    logForDebugging(f"[vivian in Chrome] Created Chrome native host wrapper script: {wrapper_path}")
    return wrapper_path


def _isChromeExtensionInstalledCachedMayBeStale() -> bool:
    asyncio.ensure_future(_update_extension_cache())
    cached = get_global_config().get("cachedChromeExtensionInstalled")
    return cached or False


async def _update_extension_cache() -> None:
    try:
        browser_paths = getAllBrowserDataPathsPortable()
        is_installed = await isChromeExtensionInstalledPortable(browser_paths)
        if not is_installed:
            return
        config = get_global_config()
        if config.get("cachedChromeExtensionInstalled") != is_installed:
            save_global_config(lambda prev: {**prev, "cachedChromeExtensionInstalled": is_installed})
    except Exception:
        pass


async def isChromeExtensionInstalled() -> bool:
    browser_paths = getAllBrowserDataPaths()
    if not browser_paths:
        logForDebugging(f"[vivian in Chrome] Unsupported platform for extension detection: {_get_platform()}")
        return False
    return await isChromeExtensionInstalledPortable(browser_paths, logForDebugging)


def _get_platform() -> str:
    import platform
    system = platform.system()
    if system == "Darwin":
        return "macos"
    if system == "Windows":
        return "windows"
    return "linux"


should_enable_vivian_in_chrome = shouldEnablevivianInChrome
should_auto_enable_vivian_in_chrome = shouldAutoEnablevivianInChrome
setup_vivian_in_chrome = setupvivianInChrome
get_native_messaging_hosts_dirs = getNativeMessagingHostsDirs
install_chrome_native_host_manifest = installChromeNativeHostManifest
register_windows_native_hosts = registerWindowsNativeHosts
create_wrapper_script = createWrapperScript
is_chrome_extension_installed_cached_may_be_stale = _isChromeExtensionInstalledCachedMayBeStale
is_chrome_extension_installed = isChromeExtensionInstalled

