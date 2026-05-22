"""ConfigTool UI — mirrors src/tools/ConfigTool/UI.tsx."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional


def _json_stringify(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=True, sort_keys=True)
    except TypeError:
        return str(value)


def renderToolUseMessage(inputData: Dict[str, Any]) -> Optional[str]:
    """Render the tool use message for ConfigTool."""
    setting = inputData.get("setting") or inputData.get("key")
    if not setting:
        return None
    if inputData.get("value") is None:
        return f"Getting {setting}"
    return f"Setting {setting} to {_json_stringify(inputData.get('value'))}"


def renderToolResultMessage(output: Dict[str, Any]) -> Optional[str]:
    """Render the tool result message for ConfigTool."""
    if not output.get("success", True):
        return f"Failed: {output.get('error', 'Unknown error')}"
    if output.get("operation") == "get":
        return f"{output.get('setting', '')} = {_json_stringify(output.get('value'))}"
    if output.get("operation") == "set":
        return f"Set {output.get('setting', '')} to {_json_stringify(output.get('newValue'))}"
    if output.get("operation") == "list":
        config = output.get("config") or {}
        if isinstance(config, dict):
            return _json_stringify(config)
    return None


def renderToolUseRejectedMessage() -> str:
    return "Config change rejected"

def renderToolUseErrorMessage(errorMessage: str) -> str:
    """Render an error message for ConfigTool."""
    return f"Config error: {errorMessage}"
