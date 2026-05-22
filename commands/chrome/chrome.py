"""chrome command — mirrors src/commands/chrome/chrome.tsx.

Chrome extension integration for browser-based tool execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...utils.vivianInChrome.common import vivian_IN_CHROME_MCP_SERVER_NAME
from ...utils.config import get_global_config, save_global_config

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


CHROME_EXTENSION_URL = "https://api-vivian.d0a.net/chrome"
CHROME_RECONNECT_URL = "https://api-vivian.d0a.net/chrome/reconnect"
CHROME_PERMISSIONS_URL = "https://api-vivian.d0a.net/chrome/permissions"


async def call(args: str, context: CommandContext) -> TextResult:
    """Manage Chrome extension integration."""
    from ...types.command import TextResult
    parts = args.strip().split(maxsplit=1) if args.strip() else []
    action = parts[0].lower() if parts else ""

    if not action or action == "status":
        return TextResult(await _get_chrome_status(context))

    if action in {"connect", "reconnect"}:
        return TextResult(await _reconnect_chrome(context))

    if action == "disconnect":
        return TextResult(_set_default_enabled(False))

    if action == "enable-default":
        return TextResult(_set_default_enabled(True))

    if action == "disable-default":
        return TextResult(_set_default_enabled(False))

    if action == "permissions":
        return TextResult(f"Manage Chrome permissions: {CHROME_PERMISSIONS_URL}")

    return TextResult("Usage: /chrome [status|connect|reconnect|disconnect|enable-default|disable-default|permissions]")


async def _get_chrome_status(context: CommandContext) -> str:
    from ...utils.auth import is_vivian_ai_subscriber
    from ...utils.vivianInChrome.setup import isChromeExtensionInstalled

    app_state = _get_app_state(context)
    mcp_clients = _get_mcp_clients(app_state)
    chrome_client = next(
        (client for client in mcp_clients if _client_value(client, "name") == vivian_IN_CHROME_MCP_SERVER_NAME),
        None,
    )
    is_connected = _client_value(chrome_client, "type") == "connected"
    is_installed = False
    try:
        is_installed = await isChromeExtensionInstalled()
    except Exception:
        is_installed = False

    config = get_global_config()
    default_enabled = bool(config.get("vivianInChromeDefaultEnabled", False))
    paired = config.get("chromeExtension") or {}
    paired_name = paired.get("pairedDeviceName")

    lines = ["vivian in Chrome"]
    lines.append(f"Status: {'Enabled' if is_connected else 'Disabled'}")
    lines.append(f"Extension: {'Installed' if is_installed else 'Not detected'}")
    lines.append(f"Enabled by default: {'Yes' if default_enabled else 'No'}")

    if paired_name:
        lines.append(f"Paired device: {paired_name}")

    if not is_connected and not is_vivian_ai_subscriber():
        lines.append("Account: vivian in Chrome requires an api-vivian.d0a.net subscription.")

    if not is_installed:
        lines.append(f"Install extension: {CHROME_EXTENSION_URL}")
    elif not is_connected:
        lines.append(f"Reconnect extension: {CHROME_RECONNECT_URL}")

    lines.append("Learn more: https://api-vivian.d0a.net/docs/en/chrome")
    return "\n".join(lines)


async def _reconnect_chrome(context: CommandContext) -> str:
    from ...utils.vivianInChrome.setup import isChromeExtensionInstalled

    config = get_global_config()
    default_enabled = bool(config.get("vivianInChromeDefaultEnabled", False))

    is_installed = False
    try:
        is_installed = await isChromeExtensionInstalled()
    except Exception:
        pass

    message = [
        f"Reconnect extension: {CHROME_RECONNECT_URL}",
    ]
    if not is_installed:
        message.insert(0, f"Install Chrome extension first: {CHROME_EXTENSION_URL}")
    if not default_enabled:
        save_global_config(lambda prev: {**prev, "vivianInChromeDefaultEnabled": True})
        message.append("Enabled by default: Yes")
    return "\n".join(message)


def _set_default_enabled(enabled: bool) -> str:
    save_global_config(lambda prev: {**prev, "vivianInChromeDefaultEnabled": enabled})
    return f"vivian in Chrome enabled by default: {'Yes' if enabled else 'No'}"


def _client_value(client: Any, key: str, default: Any = None) -> Any:
    if isinstance(client, dict):
        return client.get(key, default)
    return getattr(client, key, default)


def _get_app_state(context: Any) -> dict[str, Any]:
    state_store = getattr(context, "state_store", None)
    if state_store is not None and hasattr(state_store, "get_state"):
        try:
            state = state_store.get_state()
            if isinstance(state, dict):
                return state
        except Exception:
            pass

    app_state = getattr(context, "app_state", None)
    if isinstance(app_state, dict):
        return app_state
    if app_state is not None:
        return getattr(app_state, "__dict__", {}) or {}
    return {}


def _get_mcp_clients(app_state: dict[str, Any]) -> list[Any]:
    mcp = app_state.get("mcp") or {}
    clients = mcp.get("clients") if isinstance(mcp, dict) else getattr(mcp, "clients", None)
    if isinstance(clients, list):
        return clients
    return []


chromeInfo = call
chrome_info = call
