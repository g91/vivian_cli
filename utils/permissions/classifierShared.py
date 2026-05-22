"""Port of src/utils/permissions/classifierShared.ts"""
from __future__ import annotations
from typing import Any, Optional, List


def extractToolUseBlock(content: List[Any], tool_name: str) -> Optional[dict]:
    """Extract a tool_use block from message content by matching tool name."""
    for block in content:
        if isinstance(block, dict) and block.get('type') == 'tool_use' and block.get('name') == tool_name:
            return block
    result = {k: v for k, v in vars(content).items() if not k.startswith("_")} if hasattr(content, "__dict__") else {}
    return result


def parseClassifierResponse(tool_use_block: Optional[dict], schema: Any) -> Optional[dict]:
    """Parse and validate classifier response from a tool_use block. Returns None if invalid."""
    if tool_use_block is None:
        return None
    input_data = tool_use_block.get('input')
    if not isinstance(input_data, dict):
        return None
    return input_data
