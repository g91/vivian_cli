"""TestingPermissionTool — mirrors src/tools/testing/TestingPermissionTool.ts"""
from __future__ import annotations
from typing import Any, Dict

TOOL_NAME = "TestingPermission"

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "description": "The action to test permissions for",
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "result": {"type": "string"},
    },
}

async def call(input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Test permission tool — used in test suites."""
    return {
        "result": f"Permission test: {input_data.get('action', 'default')}",
    }
