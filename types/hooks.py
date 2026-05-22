"""Hook types — mirrors src/types/hooks.ts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional, TypeAlias


HOOK_EVENTS = [
    "PreToolUse",
    "UserPromptSubmit",
    "SessionStart",
    "Setup",
    "SubagentStart",
    "PostToolUse",
    "PostToolUseFailure",
    "PermissionDenied",
    "Notification",
    "PermissionRequest",
    "Elicitation",
    "ElicitationResult",
    "CwdChanged",
    "FileChanged",
    "WorktreeCreate",
]

HookEvent = str


def isHookEvent(value: str) -> bool:
    return value in HOOK_EVENTS


def is_hook_event(value: str) -> bool:
    return isHookEvent(value)


@dataclass
class PromptRequestOption:
    key: str
    label: str
    description: Optional[str] = None


@dataclass
class PromptRequest:
    prompt: str
    message: str
    options: list[PromptRequestOption] = field(default_factory=list)


@dataclass
class PromptResponse:
    prompt_response: str
    selected: str


@dataclass
class SyncHookResponse:
    continue_: Optional[bool] = None
    suppressOutput: Optional[bool] = None
    stopReason: Optional[str] = None
    decision: Optional[Literal["approve", "block"]] = None
    reason: Optional[str] = None
    systemMessage: Optional[str] = None
    hookSpecificOutput: Optional[dict[str, Any]] = None


@dataclass
class AsyncHookResponse:
    async_: bool = True


HookJSONOutput: TypeAlias = SyncHookResponse | AsyncHookResponse


def isSyncHookJSONOutput(json: HookJSONOutput) -> bool:
    return isinstance(json, SyncHookResponse)


def isAsyncHookJSONOutput(json: HookJSONOutput) -> bool:
    return isinstance(json, AsyncHookResponse)


@dataclass
class HookBlockingError:
    blockingError: str
    command: str


@dataclass
class HookResult:
    outcome: Literal["success", "blocking", "non_blocking_error", "cancelled"]
    message: Optional[Any] = None
    systemMessage: Optional[Any] = None
    blockingError: Optional[HookBlockingError] = None
    preventContinuation: Optional[bool] = None
    stopReason: Optional[str] = None
    permissionBehavior: Optional[str] = None
    hookPermissionDecisionReason: Optional[str] = None
    additionalContext: Optional[str] = None
    initialUserMessage: Optional[str] = None
    updatedInput: Optional[dict[str, Any]] = None
    updatedMCPToolOutput: Optional[Any] = None
    permissionRequestResult: Optional[Any] = None
    retry: Optional[bool] = None


@dataclass
class AggregatedHookResult:
    message: Optional[Any] = None
    blockingErrors: Optional[list[HookBlockingError]] = None
    preventContinuation: Optional[bool] = None
    stopReason: Optional[str] = None
    hookPermissionDecisionReason: Optional[str] = None
    permissionBehavior: Optional[str] = None
    additionalContexts: Optional[list[str]] = None
    initialUserMessage: Optional[str] = None
    updatedInput: Optional[dict[str, Any]] = None
    updatedMCPToolOutput: Optional[Any] = None
    permissionRequestResult: Optional[Any] = None
    retry: Optional[bool] = None
