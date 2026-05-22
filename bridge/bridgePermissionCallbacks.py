"""Port of src/bridge/bridgePermissionCallbacks.ts

Types and utilities for bridge permission request/response callbacks.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Literal, Optional, TypedDict


class BridgePermissionResponse(TypedDict, total=False):
    behavior: Literal["allow", "deny"]
    updatedInput: Optional[Dict[str, Any]]
    updatedPermissions: Optional[List[Any]]
    message: Optional[str]


class BridgePermissionCallbacks:
    """Interface for bridge permission request/response callbacks."""

    def sendRequest(
        self,
        request_id: str,
        tool_name: str,
        input_: Dict[str, Any],
        tool_use_id: str,
        description: str,
        permission_suggestions: Optional[List[Any]] = None,
        blocked_path: Optional[str] = None,
    ) -> None:
        raise NotImplementedError

    def sendResponse(self, request_id: str, response: BridgePermissionResponse) -> None:
        raise NotImplementedError

    def cancelRequest(self, request_id: str) -> None:
        raise NotImplementedError

    def onResponse(
        self,
        request_id: str,
        handler: Callable[[BridgePermissionResponse], None],
    ) -> Callable[[], None]:
        """Register a response handler. Returns an unsubscribe function."""
        raise NotImplementedError


def isBridgePermissionResponse(value: Any) -> bool:
    """Type predicate for validating a parsed control_response as BridgePermissionResponse."""
    if not isinstance(value, dict):
        return False
    return value.get("behavior") in ("allow", "deny")
