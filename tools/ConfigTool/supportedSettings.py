"""Supported settings — mirrors src/tools/ConfigTool/supportedSettings.ts"""
from typing import Any, Dict, List

SUPPORTED_SETTINGS: Dict[str, Dict[str, Any]] = {
    "model": {
        "description": "The model to use for conversations",
        "type": "string",
        "default": "vivian-sonnet-4-20250514",
    },
    "maxTokens": {
        "description": "Maximum tokens in the response",
        "type": "number",
        "default": 16000,
    },
    "temperature": {
        "description": "Temperature for response generation",
        "type": "number",
        "default": 0.7,
    },
    "permissionMode": {
        "description": "Permission mode for tool execution",
        "type": "string",
        "default": "default",
        "options": ["default", "acceptEdits", "bypassPermissions", "plan"],
    },
    "enableAutoCompact": {
        "description": "Automatically compact conversation when approaching context limit",
        "type": "boolean",
        "default": True,
    },
    "verbose": {
        "description": "Show verbose output including tool calls and responses",
        "type": "boolean",
        "default": False,
    },
}

def getSupportedSettings() -> Dict[str, Dict[str, Any]]:
    """Return the dict of supported settings."""
    return SUPPORTED_SETTINGS

def getSettingDefault(name: str) -> Any:
    """Get the default value for a setting."""
    setting = SUPPORTED_SETTINGS.get(name)
    return setting["default"] if setting else None

def getSettingType(name: str) -> str:
    """Get the type of a setting."""
    setting = SUPPORTED_SETTINGS.get(name)
    return setting["type"] if setting else "string"
