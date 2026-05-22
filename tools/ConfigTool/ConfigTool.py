"""ConfigTool — mirrors src/tools/ConfigTool/ConfigTool.tsx"""
from __future__ import annotations

from typing import Any, Dict

from ...utils.settings.settings import (
    getMergedSettings,
    getSettingsForSource,
    updateSettingsForSource,
)
from .supportedSettings import SUPPORTED_SETTINGS

TOOL_NAME = "Config"

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "setting": {
            "type": "string",
            "description": "The setting key (for example: theme, model, permissionMode)",
        },
        "value": {
            "description": "The new setting value. Omit to read the current value.",
        },
        "action": {
            "type": "string",
            "enum": ["get", "set", "delete", "list"],
            "description": "Legacy compatibility field. Prefer using setting plus optional value.",
        },
        "key": {"type": "string", "description": "Legacy alias for setting"},
        "scope": {
            "type": "string",
            "enum": ["local", "global", "project"],
            "description": "Optional write/read scope. Defaults to merged reads and global writes.",
        },
    },
}


async def description() -> str:
    return "Read or write Vivian/vivian Code configuration."


async def prompt() -> str:
    return (
        "Use this tool to get or set vivian Code configuration settings. "
        "Provide setting to read the current value, and include value to update it. "
        "Supports optional scope values: global, project, local."
    )


def _source_for_scope(scope: Any) -> str:
    mapping = {
        "global": "userSettings",
        "project": "projectSettings",
        "local": "localSettings",
    }
    return mapping.get(str(scope).strip().lower(), "userSettings")


def _get_nested(data: Dict[str, Any], setting: str) -> Any:
    current: Any = data
    for part in setting.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _set_nested(data: Dict[str, Any], setting: str, value: Any) -> Dict[str, Any]:
    updated = dict(data)
    current = updated
    parts = setting.split(".")
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
        else:
            child = dict(child)
        current[part] = child
        current = child
    current[parts[-1]] = value
    return updated


def _delete_nested(data: Dict[str, Any], setting: str) -> Dict[str, Any]:
    updated = dict(data)
    current = updated
    parents: list[tuple[Dict[str, Any], str]] = []
    parts = setting.split(".")
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            return updated
        child_copy = dict(child)
        current[part] = child_copy
        parents.append((current, part))
        current = child_copy
    current.pop(parts[-1], None)

    for parent, key in reversed(parents):
        child = parent.get(key)
        if isinstance(child, dict) and not child:
            parent.pop(key, None)
    return updated


def _coerce_value(setting: str, value: Any) -> tuple[Any, str | None]:
    config = SUPPORTED_SETTINGS.get(setting)
    if config is None:
        return value, f'Unknown setting: "{setting}"'

    expected_type = config.get("type")
    final_value = value
    if expected_type == "boolean":
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered == "true":
                final_value = True
            elif lowered == "false":
                final_value = False
        if not isinstance(final_value, bool):
            return value, f"{setting} requires true or false."
    elif expected_type == "number":
        if isinstance(value, str):
            try:
                final_value = float(value) if "." in value else int(value)
            except ValueError:
                return value, f"{setting} requires a numeric value."
        elif not isinstance(value, (int, float)) or isinstance(value, bool):
            return value, f"{setting} requires a numeric value."
    elif expected_type == "string":
        if not isinstance(final_value, str):
            final_value = str(final_value)

    options = config.get("options")
    if options and final_value not in options:
        return final_value, f'Invalid value "{final_value}". Options: {", ".join(options)}'
    return final_value, None


async def call(input_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    setting = input_data.get("setting") or input_data.get("key")
    has_value = "value" in input_data
    action = input_data.get("action")
    scope = input_data.get("scope")

    if action == "list" or (not setting and not has_value):
        merged = getMergedSettings()
        supported = {
            name: _get_nested(merged, name)
            for name in SUPPORTED_SETTINGS
        }
        return {"success": True, "operation": "list", "config": supported}

    if not setting:
        return {"success": False, "error": "Missing setting"}

    if setting not in SUPPORTED_SETTINGS:
        return {"success": False, "error": f'Unknown setting: "{setting}"'}

    if action == "delete":
        source = _source_for_scope(scope)
        current_source = getSettingsForSource(source) or {}
        previous = _get_nested(current_source, setting)
        updateSettingsForSource(source, _delete_nested(current_source, setting))
        return {
            "success": True,
            "operation": "set",
            "setting": setting,
            "previousValue": previous,
            "newValue": None,
            "value": None,
        }

    if not has_value or action == "get":
        current = _get_nested(getMergedSettings(), setting)
        return {
            "success": True,
            "operation": "get",
            "setting": setting,
            "value": current,
        }

    final_value, error = _coerce_value(setting, input_data.get("value"))
    if error:
        return {
            "success": False,
            "operation": "set",
            "setting": setting,
            "error": error,
        }

    source = _source_for_scope(scope)
    current_source = getSettingsForSource(source) or {}
    previous = _get_nested(current_source, setting)
    updated_source = _set_nested(current_source, setting, final_value)
    updateSettingsForSource(source, updated_source)
    return {
        "success": True,
        "operation": "set",
        "setting": setting,
        "previousValue": previous,
        "newValue": final_value,
        "value": final_value,
    }
