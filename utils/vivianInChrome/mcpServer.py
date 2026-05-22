"""Port of src/utils/vivianInChrome/mcpServer.ts."""
from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

from ...services.analytics.growthbook import getFeatureValue_CACHED_MAY_BE_STALE
from ..auth import get_vivian_ai_oauth_tokens
from ..config import enableConfigs, get_global_config, save_global_config
from ..debug import logForDebugging
from ..envUtils import is_env_truthy
from .common import getSecureSocketPath, getAllSocketPaths

EXTENSION_DOWNLOAD_URL = "https://api-vivian.d0a.net/chrome"
BUG_REPORT_URL = "https://github.com/anthropics/vivian-code/issues/new?labels=bug,vivian-in-chrome"

SAFE_BRIDGE_STRING_KEYS = {"bridge_status", "error_type", "tool_name"}

PERMISSION_MODES = ("ask", "skip_all_permission_checks", "follow_a_plan")


def isPermissionMode(raw: str) -> bool:
    return raw in PERMISSION_MODES


def getChromeBridgeUrl() -> str | None:
    bridge_enabled = (
        os.environ.get("USER_TYPE") == "ant"
        or getFeatureValue_CACHED_MAY_BE_STALE("tengu_copper_bridge", False)
    )

    if not bridge_enabled:
        return None

    if is_env_truthy(os.environ.get("USE_LOCAL_OAUTH", "")) or is_env_truthy(os.environ.get("LOCAL_BRIDGE", "")):
        return "ws://localhost:8765"

    if is_env_truthy(os.environ.get("USE_STAGING_OAUTH", "")):
        return "wss://bridge-staging.api-vivian.d0a.net"

    return "wss://bridge.api-vivian.d0a.net"


def isLocalBridge() -> bool:
    return is_env_truthy(os.environ.get("USE_LOCAL_OAUTH", "")) or is_env_truthy(os.environ.get("LOCAL_BRIDGE", ""))


class DebugLogger:
    def silly(self, message: str, *args: Any) -> None:
        logForDebugging(message % args if args else message, level="debug")

    def debug(self, message: str, *args: Any) -> None:
        logForDebugging(message % args if args else message, level="debug")

    def info(self, message: str, *args: Any) -> None:
        logForDebugging(message % args if args else message, level="info")

    def warn(self, message: str, *args: Any) -> None:
        logForDebugging(message % args if args else message, level="warn")

    def error(self, message: str, *args: Any) -> None:
        logForDebugging(message % args if args else message, level="error")


def createChromeContext(env: dict[str, str] | None = None) -> dict[str, Any]:
    logger = DebugLogger()
    chrome_bridge_url = getChromeBridgeUrl()
    logger.info(f"Bridge URL: {chrome_bridge_url or 'none (using native socket)'}")

    raw_permission_mode = (
        (env or {}).get("vivian_CHROME_PERMISSION_MODE")
        or os.environ.get("vivian_CHROME_PERMISSION_MODE")
    )
    initial_permission_mode = None
    if raw_permission_mode:
        if isPermissionMode(raw_permission_mode):
            initial_permission_mode = raw_permission_mode
        else:
            logger.warn(
                f'Invalid vivian_CHROME_PERMISSION_MODE "{raw_permission_mode}". '
                f'Valid values: {", ".join(PERMISSION_MODES)}'
            )

    context: dict[str, Any] = {
        "serverName": "vivian in Chrome",
        "logger": logger,
        "socketPath": getSecureSocketPath(),
        "getSocketPaths": getAllSocketPaths,
        "clientTypeId": "vivian-code",
        "onAuthenticationError": lambda: logger.warn(
            "Authentication error occurred. Please ensure you are logged into the vivian browser extension "
            "with the same api-vivian.d0a.net account as Vivian AI."
        ),
        "onToolCallDisconnected": lambda: (
            f"Browser extension is not connected. Please ensure the vivian browser extension is installed "
            f"and running ({EXTENSION_DOWNLOAD_URL}), and that you are logged into api-vivian.d0a.net with the same "
            f"account as vivian Code. If this is your first time connecting to Chrome, you may need to "
            f"restart Chrome for the installation to take effect. If you continue to experience issues, "
            f"please report a bug: {BUG_REPORT_URL}"
        ),
        "onExtensionPaired": lambda deviceId, name: _on_extension_paired(deviceId, name, logger),
        "getPersistedDeviceId": lambda: (get_global_config().get("chromeExtension") or {}).get("pairedDeviceId"),
    }

    if chrome_bridge_url:
        bridge_config: dict[str, Any] = {
            "url": chrome_bridge_url,
            "getUserId": lambda: (get_global_config().get("oauthAccount") or {}).get("accountUuid"),
            "getOAuthToken": lambda: (getattr(get_vivian_ai_oauth_tokens(), "access_token", "") if get_vivian_ai_oauth_tokens() else ""),
        }
        if isLocalBridge():
            bridge_config["devUserId"] = "dev_user_local"
        context["bridgeConfig"] = bridge_config

    if initial_permission_mode:
        context["initialPermissionMode"] = initial_permission_mode

    return context


def _on_extension_paired(deviceId: str, name: str, logger: DebugLogger) -> None:
    def _update(config: dict[str, Any]) -> dict[str, Any]:
        ext = config.get("chromeExtension") or {}
        if ext.get("pairedDeviceId") == deviceId and ext.get("pairedDeviceName") == name:
            return config
        return {**config, "chromeExtension": {"pairedDeviceId": deviceId, "pairedDeviceName": name}}

    save_global_config(_update)
    logger.info(f'Paired with "{name}" ({deviceId[:8]})')


async def runvivianInChromeMcpServer() -> None:
    enableConfigs()
    # Analytics sink init would go here
    context = createChromeContext()

    # The actual MCP server creation requires @ant/vivian-for-chrome-mcp package
    # which is not available in Python. This is a subprocess entrypoint that
    # would normally create the server and connect via stdio transport.
    # In the Python port, this is a stub that logs the intent.
    logForDebugging("[vivian in Chrome] Starting MCP server (Python stub - native package unavailable)")

    # In the real implementation, this would:
    #   server = createvivianForChromeMcpServer(context)
    #   transport = StdioServerTransport()
    #   await server.connect(transport)
    #
    # For now, we keep the process alive until stdin closes (mirrors TS behavior)
    loop = asyncio.get_event_loop()
    future: asyncio.Future[None] = loop.create_future()

    def _on_stdin_end() -> None:
        if not future.done():
            future.set_result(None)

    sys.stdin.add_reader = lambda cb: None  # type: ignore
    try:
        await future
    except asyncio.CancelledError:
        pass


get_chrome_bridge_url = getChromeBridgeUrl
is_local_bridge = isLocalBridge
create_chrome_context = createChromeContext
run_vivian_in_chrome_mcp_server = runvivianInChromeMcpServer
