"""SDK core types.

Python port of src/entrypoints/sdk/coreTypes.ts.
"""
from __future__ import annotations

from typing import Any, TypeAlias

from ...types.hooks import HOOK_EVENTS
from ..sandboxTypes import (
	SandboxFilesystemConfig,
	SandboxIgnoreViolations,
	SandboxNetworkConfig,
	SandboxSettings,
)

SDKMessage: TypeAlias = dict[str, Any]
SDKResultMessage: TypeAlias = dict[str, Any]
SDKUserMessage: TypeAlias = dict[str, Any]
SDKSessionInfo: TypeAlias = dict[str, Any]
NonNullableUsage: TypeAlias = dict[str, Any]

EXIT_REASONS = [
	"clear",
	"resume",
	"logout",
	"prompt_input_exit",
	"other",
	"bypass_permissions_disabled",
]

CoreTypes = dict[str, Any]

__all__ = [
	"CoreTypes",
	"SandboxFilesystemConfig",
	"SandboxIgnoreViolations",
	"SandboxNetworkConfig",
	"SandboxSettings",
	"SDKMessage",
	"SDKResultMessage",
	"SDKSessionInfo",
	"SDKUserMessage",
	"NonNullableUsage",
	"HOOK_EVENTS",
	"EXIT_REASONS",
]
