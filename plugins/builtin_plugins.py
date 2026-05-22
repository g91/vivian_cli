"""Built-in Plugin Registry — mirrors src/plugins/builtinPlugins.ts.

Manages built-in plugins that ship with the CLI and can be enabled/disabled
by users via the /plugin UI.

Plugin IDs use the format `{name}@builtin` to distinguish them from
marketplace plugins (`{name}@{marketplace}`).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

BUILTIN_MARKETPLACE_NAME = "builtin"

_BUILTIN_PLUGINS: dict[str, dict] = {}


def registerBuiltinPlugin(definition: dict) -> None:
    """Register a built-in plugin. Call from initBuiltinPlugins() at startup."""
    _BUILTIN_PLUGINS[definition["name"]] = definition


def isBuiltinPluginId(pluginId: str) -> bool:
    """Check if a plugin ID represents a built-in plugin (ends with @builtin)."""
    return pluginId.endswith(f"@{BUILTIN_MARKETPLACE_NAME}")


def getBuiltinPluginDefinition(name: str) -> Optional[dict]:
    """Get a specific built-in plugin definition by name."""
    return _BUILTIN_PLUGINS.get(name)


def _loadSettings() -> dict:
    try:
        path = Path.home() / ".vivian" / "settings.json"
        return json.loads(path.read_text())
    except Exception:
        return {}


def getBuiltinPlugins() -> dict[str, list[dict]]:
    """Return {"enabled": [...], "disabled": [...]} for all registered built-ins.

    Plugins whose isAvailable() returns False are omitted entirely.
    Enabled state: user preference > plugin default > True.
    """
    settings = _loadSettings()
    enabledMap: dict = settings.get("enabledPlugins", {})
    enabled: list[dict] = []
    disabled: list[dict] = []

    for name, definition in _BUILTIN_PLUGINS.items():
        isAvailable = definition.get("isAvailable")
        if callable(isAvailable) and not isAvailable():
            continue

        pluginId = f"{name}@{BUILTIN_MARKETPLACE_NAME}"
        userSetting = enabledMap.get(pluginId)
        defaultEnabled = definition.get("defaultEnabled", True)
        isEnabled: Any = userSetting if userSetting is not None else defaultEnabled
        if isEnabled is None:
            isEnabled = True

        plugin: dict = {
            "name": name,
            "manifest": {
                "name": name,
                "description": definition.get("description"),
                "version": definition.get("version"),
            },
            "path": BUILTIN_MARKETPLACE_NAME,
            "source": pluginId,
            "repository": pluginId,
            "enabled": bool(isEnabled),
            "isBuiltin": True,
            "hooksConfig": definition.get("hooks"),
            "mcpServers": definition.get("mcpServers"),
        }
        (enabled if isEnabled else disabled).append(plugin)

    return {"enabled": enabled, "disabled": disabled}


def getBuiltinPluginSkillCommands() -> list[dict]:
    """Get skills from enabled built-in plugins as Command dicts."""
    result = getBuiltinPlugins()
    commands: list[dict] = []

    for plugin in result["enabled"]:
        definition = _BUILTIN_PLUGINS.get(plugin["name"])
        if not definition:
            continue
        skills = definition.get("skills")
        if not skills:
            continue
        for skill in skills:
            commands.append(_skillDefinitionToCommand(skill))

    return commands


def clearBuiltinPlugins() -> None:
    """Clear built-in plugins registry (for testing)."""
    _BUILTIN_PLUGINS.clear()


# -- private

def _skillDefinitionToCommand(definition: dict) -> dict:
    """Convert a BundledSkillDefinition to a Command dict."""
    return {
        "type": "prompt",
        "name": definition.get("name"),
        "description": definition.get("description"),
        "hasUserSpecifiedDescription": True,
        "allowedTools": definition.get("allowedTools", []),
        "argumentHint": definition.get("argumentHint"),
        "whenToUse": definition.get("whenToUse"),
        "model": definition.get("model"),
        "disableModelInvocation": definition.get("disableModelInvocation", False),
        "userInvocable": definition.get("userInvocable", True),
        "contentLength": 0,
        "source": "bundled",
        "loadedFrom": "bundled",
        "hooks": definition.get("hooks"),
        "context": definition.get("context"),
        "agent": definition.get("agent"),
        "isEnabled": definition.get("isEnabled", lambda: True),
        "isHidden": not definition.get("userInvocable", True),
        "progressMessage": "running",
        "getPromptForCommand": definition.get("getPromptForCommand"),
    }
