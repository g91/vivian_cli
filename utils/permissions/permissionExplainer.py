"""Port of src/utils/permissions/permissionExplainer.ts"""
from __future__ import annotations
import json
from typing import Optional, Dict, Any, List


def isPermissionExplainerEnabled() -> bool:
    """Return whether the permission explainer feature is enabled."""
    try:
        from ..utils.config import getGlobalConfig
        config = getGlobalConfig()
        return config.get('permissionExplainerEnabled', True) is not False
    except Exception:
        return True


async def generatePermissionExplanation(
    tool_name: str,
    tool_input: Any,
    tool_description: Optional[str] = None,
    messages: Optional[List[Any]] = None,
    signal: Optional[Any] = None,
) -> Optional[Dict[str, str]]:
    """Generate a permission explanation for a tool use request. Returns None if disabled."""
    if not isPermissionExplainerEnabled():
        return None
    # In Python port, we return a basic explanation without LLM call
    input_str = json.dumps(tool_input, indent=2) if not isinstance(tool_input, str) else tool_input
    return {
        'riskLevel': 'MEDIUM',
        'explanation': f'Running {tool_name} command',
        'reasoning': f'I need to use {tool_name} to complete this task',
        'risk': 'Depends on the specific command being executed',
    }
