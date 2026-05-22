"""plugin command — mirrors src/commands/plugin/plugin.tsx.

Manage plugins: install, uninstall, enable, disable, list.
"""

from __future__ import annotations

import contextlib
import io
from typing import TYPE_CHECKING

from ...services.plugins import disablePlugin, enablePlugin, installPlugin, uninstallPlugin

if TYPE_CHECKING:
    from ...types.command import CommandContext, TextResult


async def _run_action(action) -> str:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        await action
    return buffer.getvalue().strip()


async def call(args: str, context: CommandContext) -> TextResult:
    from ...types.command import TextResult
    parts = args.strip().split(maxsplit=2) if args.strip() else []
    action = parts[0].lower() if parts else ""

    if not action or action == "list":
        return TextResult(_list_plugins(context))

    if action == "install" and len(parts) >= 2:
        name = parts[1]
        output = await _run_action(installPlugin(name))
        return TextResult(output or f"Plugin installed: {name}")

    if action == "uninstall" and len(parts) >= 2:
        name = parts[1]
        if name in _get_plugins(context):
            output = await _run_action(uninstallPlugin(name))
            return TextResult(output or f"Plugin uninstalled: {name}")
        return TextResult(f"Plugin not found: {name}")

    if action == "enable" and len(parts) >= 2:
        name = parts[1]
        if name in _get_plugins(context):
            output = await _run_action(enablePlugin(name))
            return TextResult(output or f"Plugin enabled: {name}")
        return TextResult(f"Plugin not found: {name}")

    if action == "disable" and len(parts) >= 2:
        name = parts[1]
        if name in _get_plugins(context):
            output = await _run_action(disablePlugin(name))
            return TextResult(output or f"Plugin disabled: {name}")
        return TextResult(f"Plugin not found: {name}")

    return TextResult("Usage: /plugin [list|install <name>|uninstall <name>|enable <name>|disable <name>]")


def _get_plugins(context: CommandContext) -> dict:
    try:
        from ...cli.handlers.plugins import _load_installed_plugins, _load_settings

        plugins = _load_installed_plugins()
        settings = _load_settings()
        enabled_map = settings.get("enabledPlugins") or {}

        normalized: dict[str, dict] = {}
        for name, info in plugins.items():
            if not isinstance(info, dict):
                info = {}
            normalized[name] = {
                **info,
                "enabled": enabled_map.get(name, info.get("defaultEnabled", True)),
            }
        return normalized
    except Exception:
        return {}


def _save_plugins(context: CommandContext, plugins: dict) -> None:
    del context, plugins


def _list_plugins(context: CommandContext) -> str:
    plugins = _get_plugins(context)
    if not plugins:
        return "No plugins installed.\nUse /plugin install <name> to install one."
    lines = ["Installed Plugins:", ""]
    for name, cfg in plugins.items():
        status = "✓ enabled" if cfg.get("enabled", True) else "✗ disabled"
        lines.append(f"  {name} ({cfg.get('version', 'latest')}) — {status}")
    return "\n".join(lines)


pluginInfo = _list_plugins
plugin_info = _list_plugins
