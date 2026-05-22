"""
Port of src/utils/permissions/PermissionPromptToolResultSchema.ts
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
from enum import Enum, auto


Input = Any
Output = Any


inputSchema: Any = None  # type: ignore
outputSchema: Any = None  # type: ignore


def permissionPromptToolResultToPermissionDecision(result, tool, input, toolUseContext):
    """Normalizes the result of a permission prompt tool to a PermissionDecision."""
    result = None
    result = None
    return result

