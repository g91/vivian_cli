"""Permission types and constants — mirrors src/types/permissions.ts."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Final, Literal, Optional, TypeAlias


EXTERNAL_PERMISSION_MODES: Final = (
    "acceptEdits",
    "bypassPermissions",
    "default",
    "dontAsk",
    "plan",
)

ExternalPermissionMode = Literal["acceptEdits", "bypassPermissions", "default", "dontAsk", "plan"]
InternalPermissionMode = Literal["acceptEdits", "bypassPermissions", "default", "dontAsk", "plan", "auto", "bubble"]
PermissionMode = InternalPermissionMode


def _is_env_truthy(val: str | None) -> bool:
    return val is not None and val.lower() not in ("", "0", "false", "no")


_has_transcript_classifier = _is_env_truthy(os.environ.get("vivian_CODE_TRANSCRIPT_CLASSIFIER"))

INTERNAL_PERMISSION_MODES: tuple[str, ...] = (
    *EXTERNAL_PERMISSION_MODES,
    *(("auto",) if _has_transcript_classifier else ()),
)
PERMISSION_MODES = INTERNAL_PERMISSION_MODES

PermissionBehavior = Literal["allow", "deny", "ask"]
PermissionRuleSource = Literal[
    "userSettings",
    "projectSettings",
    "localSettings",
    "flagSettings",
    "policySettings",
    "cliArg",
    "command",
    "session",
]
PermissionUpdateDestination = Literal[
    "userSettings",
    "projectSettings",
    "localSettings",
    "session",
    "cliArg",
]
WorkingDirectorySource = PermissionRuleSource


@dataclass
class PermissionRuleValue:
    toolName: str
    ruleContent: Optional[str] = None

    @property
    def tool_name(self) -> str:
        return self.toolName

    @property
    def rule_content(self) -> Optional[str]:
        return self.ruleContent


@dataclass
class PermissionRule:
    source: PermissionRuleSource
    ruleBehavior: PermissionBehavior
    ruleValue: PermissionRuleValue

    @property
    def rule_behavior(self) -> PermissionBehavior:
        return self.ruleBehavior

    @property
    def rule_value(self) -> PermissionRuleValue:
        return self.ruleValue


@dataclass
class AdditionalWorkingDirectory:
    path: str
    source: WorkingDirectorySource


@dataclass
class PermissionCommandMetadata:
    name: str
    description: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)


PermissionMetadata: TypeAlias = dict[str, PermissionCommandMetadata] | None


@dataclass
class PermissionAllowDecision:
    behavior: Literal["allow"] = "allow"
    updatedInput: Optional[dict[str, Any]] = None
    userModified: Optional[bool] = None
    decisionReason: Optional[Any] = None
    toolUseID: Optional[str] = None
    acceptFeedback: Optional[str] = None
    contentBlocks: Optional[list[Any]] = None


@dataclass
class PendingClassifierCheck:
    command: str
    cwd: str
    descriptions: list[str]


@dataclass
class PermissionAskDecision:
    behavior: Literal["ask"] = "ask"
    message: str = ""
    updatedInput: Optional[dict[str, Any]] = None
    decisionReason: Optional[Any] = None
    suggestions: Optional[list["PermissionUpdate"]] = None
    blockedPath: Optional[str] = None
    metadata: Optional[PermissionMetadata] = None
    isBashSecurityCheckForMisparsing: Optional[bool] = None
    pendingClassifierCheck: Optional[PendingClassifierCheck] = None
    contentBlocks: Optional[list[Any]] = None


@dataclass
class PermissionDenyDecision:
    behavior: Literal["deny"] = "deny"
    message: str = ""
    decisionReason: Optional[Any] = None
    toolUseID: Optional[str] = None


@dataclass
class PermissionPassthroughResult:
    behavior: Literal["passthrough"] = "passthrough"
    message: str = ""
    decisionReason: Optional[Any] = None
    suggestions: Optional[list["PermissionUpdate"]] = None
    blockedPath: Optional[str] = None
    pendingClassifierCheck: Optional[PendingClassifierCheck] = None


PermissionDecision: TypeAlias = PermissionAllowDecision | PermissionAskDecision | PermissionDenyDecision
PermissionResult: TypeAlias = PermissionDecision | PermissionPassthroughResult


@dataclass
class PermissionUpdate:
    type: Literal["addRules", "replaceRules", "removeRules", "setMode", "addDirectories", "removeDirectories"]
    destination: PermissionUpdateDestination
    rules: Optional[list[PermissionRuleValue]] = None
    behavior: Optional[PermissionBehavior] = None
    mode: Optional[ExternalPermissionMode] = None
    directories: Optional[list[str]] = None
