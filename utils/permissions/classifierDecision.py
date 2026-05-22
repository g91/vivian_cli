"""Port of src/utils/permissions/classifierDecision.ts"""
from __future__ import annotations
from typing import Set

# Safe tools that don't need classifier checking
SAFE_YOLO_ALLOWLISTED_TOOLS: Set[str] = {
    'Read',
    'Grep',
    'Glob',
    'LSP',
    'ToolSearch',
    'ListMcpResources',
    'ReadMcpResourceTool',
    'TodoWrite',
    'TaskCreate',
    'TaskGet',
    'TaskUpdate',
    'TaskList',
    'TaskStop',
    'TaskOutput',
    'AskUserQuestion',
    'EnterPlanMode',
    'ExitPlanMode',
    'TeamCreate',
    'TeamDelete',
    'SendMessage',
    'Sleep',
    'YoloClassifier',
}


def isAutoModeAllowlistedTool(tool_name: str) -> bool:
    """Return True if the tool is safe and doesn't need classifier checking."""
    return tool_name in SAFE_YOLO_ALLOWLISTED_TOOLS
