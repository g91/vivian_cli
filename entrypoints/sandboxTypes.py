"""Sandbox types for the Vivian Agent SDK.

Python port of src/entrypoints/sandboxTypes.ts.
"""
from __future__ import annotations

from typing import Any, TypedDict

from ..utils.lazySchema import lazy_schema


class SandboxNetworkConfig(TypedDict, total=False):
	allowedDomains: list[str]
	allowManagedDomainsOnly: bool
	allowUnixSockets: list[str]
	allowAllUnixSockets: bool
	allowLocalBinding: bool
	httpProxyPort: int
	socksProxyPort: int


class SandboxFilesystemConfig(TypedDict, total=False):
	allowWrite: list[str]
	denyWrite: list[str]
	denyRead: list[str]
	allowRead: list[str]
	allowManagedReadPathsOnly: bool


class SandboxSettings(TypedDict, total=False):
	enabled: bool
	failIfUnavailable: bool
	autoAllowBashIfSandboxed: bool
	allowUnsandboxedCommands: bool
	network: SandboxNetworkConfig
	filesystem: SandboxFilesystemConfig
	ignoreViolations: dict[str, list[str]]
	enableWeakerNestedSandbox: bool
	enableWeakerNetworkIsolation: bool
	excludedCommands: list[str]
	ripgrep: dict[str, Any]


SandboxIgnoreViolations = dict[str, list[str]]
SandboxTypes = dict[str, Any]


def _object_schema(properties: dict[str, Any], *, description: str | None = None, optional: bool = False) -> dict[str, Any]:
	schema = {
		"kind": "object",
		"properties": properties,
		"optional": optional,
	}
	if description:
		schema["description"] = description
	return schema


SandboxNetworkConfigSchema = lazy_schema(
	lambda: _object_schema(
		{
			"allowedDomains": {"kind": "array", "items": "string", "optional": True},
			"allowManagedDomainsOnly": {"kind": "boolean", "optional": True},
			"allowUnixSockets": {"kind": "array", "items": "string", "optional": True},
			"allowAllUnixSockets": {"kind": "boolean", "optional": True},
			"allowLocalBinding": {"kind": "boolean", "optional": True},
			"httpProxyPort": {"kind": "number", "optional": True},
			"socksProxyPort": {"kind": "number", "optional": True},
		},
		description="Network configuration schema for sandbox.",
		optional=True,
	)
)

SandboxFilesystemConfigSchema = lazy_schema(
	lambda: _object_schema(
		{
			"allowWrite": {"kind": "array", "items": "string", "optional": True},
			"denyWrite": {"kind": "array", "items": "string", "optional": True},
			"denyRead": {"kind": "array", "items": "string", "optional": True},
			"allowRead": {"kind": "array", "items": "string", "optional": True},
			"allowManagedReadPathsOnly": {"kind": "boolean", "optional": True},
		},
		description="Filesystem configuration schema for sandbox.",
		optional=True,
	)
)

SandboxSettingsSchema = lazy_schema(
	lambda: _object_schema(
		{
			"enabled": {"kind": "boolean", "optional": True},
			"failIfUnavailable": {"kind": "boolean", "optional": True},
			"autoAllowBashIfSandboxed": {"kind": "boolean", "optional": True},
			"allowUnsandboxedCommands": {"kind": "boolean", "optional": True},
			"network": SandboxNetworkConfigSchema(),
			"filesystem": SandboxFilesystemConfigSchema(),
			"ignoreViolations": {"kind": "record", "key": "string", "value": {"kind": "array", "items": "string"}, "optional": True},
			"enableWeakerNestedSandbox": {"kind": "boolean", "optional": True},
			"enableWeakerNetworkIsolation": {"kind": "boolean", "optional": True},
			"excludedCommands": {"kind": "array", "items": "string", "optional": True},
			"ripgrep": {"kind": "object", "properties": {"command": {"kind": "string"}, "args": {"kind": "array", "items": "string", "optional": True}}, "optional": True},
		},
		description="Sandbox settings schema.",
	)
)


__all__ = [
	"SandboxTypes",
	"SandboxSettings",
	"SandboxNetworkConfig",
	"SandboxFilesystemConfig",
	"SandboxIgnoreViolations",
	"SandboxSettingsSchema",
	"SandboxNetworkConfigSchema",
	"SandboxFilesystemConfigSchema",
]
