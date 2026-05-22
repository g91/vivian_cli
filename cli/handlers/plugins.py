"""Plugin subcommand handlers — mirrors src/cli/handlers/plugins.ts.

Handles plugin install/uninstall/enable/disable/list and marketplace commands.
Dynamically imported when ``vivian plugin *`` runs.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from ..exit import cli_error, cli_ok

logger = logging.getLogger(__name__)

VALID_INSTALLABLE_SCOPES = {"user", "project"}
VALID_UPDATE_SCOPES = {"user", "project"}

_PLUGINS_DIR = Path.home() / ".vivian" / "plugins"
_SETTINGS_FILE = Path.home() / ".vivian" / "settings.json"


def _load_settings() -> dict:
    try:
        return json.loads(_SETTINGS_FILE.read_text())
    except Exception:
        return {}


def _save_settings(data: dict) -> None:
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(json.dumps(data, indent=2))


def _load_installed_plugins() -> dict[str, dict]:
    manifest = _PLUGINS_DIR / "installed.json"
    try:
        return json.loads(manifest.read_text())
    except Exception:
        return {}


def _save_installed_plugins(plugins: dict[str, dict]) -> None:
    _PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    (_PLUGINS_DIR / "installed.json").write_text(json.dumps(plugins, indent=2))


# ---------------------------------------------------------------------------
# List

def list_plugins_handler(show_disabled: bool = False) -> None:
    """Print installed plugins."""
    plugins = _load_installed_plugins()
    settings = _load_settings()
    enabled_map: dict[str, bool] = (settings.get("enabledPlugins") or {})
    if not plugins:
        print("No plugins installed.")
        return
    print(f"{'NAME':<30} {'VERSION':<12} STATUS")
    print("-" * 55)
    for name, info in sorted(plugins.items()):
        version = info.get("version", "?")
        is_enabled = enabled_map.get(name, info.get("defaultEnabled", True))
        status = "enabled" if is_enabled else "disabled"
        if not show_disabled and not is_enabled:
            continue
        print(f"{name:<30} {version:<12} {status}")


# ---------------------------------------------------------------------------
# Enable / Disable

def enable_plugin_handler(plugin_id: str) -> None:
    settings = _load_settings()
    ep = settings.setdefault("enabledPlugins", {})
    ep[plugin_id] = True
    _save_settings(settings)
    print(f"✔ Plugin '{plugin_id}' enabled.")


def disable_plugin_handler(plugin_id: str) -> None:
    settings = _load_settings()
    ep = settings.setdefault("enabledPlugins", {})
    ep[plugin_id] = False
    _save_settings(settings)
    print(f"✔ Plugin '{plugin_id}' disabled.")


def disable_all_plugins_handler() -> None:
    plugins = _load_installed_plugins()
    settings = _load_settings()
    ep = settings.setdefault("enabledPlugins", {})
    for name in plugins:
        ep[name] = False
    _save_settings(settings)
    print(f"✔ Disabled {len(plugins)} plugin(s).")


# ---------------------------------------------------------------------------
# Install / Uninstall

def install_plugin_handler(
    plugin_id: str,
    scope: str = "user",
    force: bool = False,
) -> None:
    if scope not in VALID_INSTALLABLE_SCOPES:
        cli_error(f"Invalid scope '{scope}'. Valid: {sorted(VALID_INSTALLABLE_SCOPES)}")
    plugins = _load_installed_plugins()
    if plugin_id in plugins and not force:
        print(f"Plugin '{plugin_id}' is already installed (use --force to reinstall).")
        return
    # Attempt marketplace lookup; falls back to local-only registration
    # when marketplace infrastructure is not available.
    try:
        import asyncio
        from ...utils.plugins.marketplaceHelpers import loadMarketplacesWithGracefulDegradation
        from ...utils.config import get_config
        marketplaces = asyncio.run(loadMarketplacesWithGracefulDegradation(get_config()))
        if marketplaces and plugin_id in marketplaces:
            entry = marketplaces[plugin_id]
            plugins[plugin_id] = {"version": entry.get("version", "latest"), "scope": scope, "defaultEnabled": True}
            _save_installed_plugins(plugins)
            print(f"✔ Plugin '{plugin_id}' installed from marketplace.")
            return
    except Exception:
        pass
    plugins[plugin_id] = {"version": "latest", "scope": scope, "defaultEnabled": True}
    _save_installed_plugins(plugins)
    print(f"✔ Plugin '{plugin_id}' installed.")


def uninstall_plugin_handler(plugin_id: str) -> None:
    plugins = _load_installed_plugins()
    if plugin_id not in plugins:
        cli_error(f"Plugin '{plugin_id}' is not installed.")
    plugins.pop(plugin_id)
    _save_installed_plugins(plugins)
    settings = _load_settings()
    settings.get("enabledPlugins", {}).pop(plugin_id, None)
    _save_settings(settings)
    print(f"✔ Plugin '{plugin_id}' uninstalled.")


# ---------------------------------------------------------------------------
# Validate

def validate_plugin_handler(path: str) -> None:
    """Validate a plugin directory for required fields."""
    p = Path(path)
    manifest_path = p / "manifest.json"
    errors: list[str] = []
    warnings: list[str] = []

    if not p.is_dir():
        cli_error(f"Not a directory: {path}")
    if not manifest_path.exists():
        errors.append("Missing manifest.json")
    else:
        try:
            manifest = json.loads(manifest_path.read_text())
            for required in ("name", "version", "description"):
                if not manifest.get(required):
                    errors.append(f"manifest.json: missing required field '{required}'")
        except json.JSONDecodeError as exc:
            errors.append(f"manifest.json: invalid JSON — {exc}")

    if errors:
        print(f"✗ Found {len(errors)} error(s):\n")
        for e in errors:
            print(f"  ▸ {e}")
        print()
    if warnings:
        print(f"⚠ Found {len(warnings)} warning(s):\n")
        for w in warnings:
            print(f"  ▸ {w}")
        print()
    if not errors and not warnings:
        print("✔ Plugin manifest is valid.")


def handle_marketplace_error(error: Exception, action: str) -> None:
    logger.error(error)
    cli_error(f"✗ Failed to {action}: {error}")
