"""SDK core schemas.

Python port of src/entrypoints/sdk/coreSchemas.ts.
The exported `*Schema` names are lazy schema descriptor factories rather than Zod schemas.
"""
from __future__ import annotations

from typing import Any

from ...types.hooks import HOOK_EVENTS
from ...types.permissions import EXTERNAL_PERMISSION_MODES
from ..sandboxTypes import SandboxFilesystemConfigSchema, SandboxNetworkConfigSchema, SandboxSettingsSchema
from ...utils.lazySchema import lazy_schema


def _enum_schema(values: list[str] | tuple[str, ...], *, description: str | None = None) -> dict[str, Any]:
	schema = {"kind": "enum", "values": list(values)}
	if description:
		schema["description"] = description
	return schema


def _object_schema(properties: dict[str, Any], *, description: str | None = None) -> dict[str, Any]:
	schema = {"kind": "object", "properties": properties}
	if description:
		schema["description"] = description
	return schema


def _array_schema(items: Any, *, description: str | None = None, optional: bool = False) -> dict[str, Any]:
	schema = {"kind": "array", "items": items, "optional": optional}
	if description:
		schema["description"] = description
	return schema


def _record_schema(value: Any, *, key: Any = "string", description: str | None = None, optional: bool = False) -> dict[str, Any]:
	schema = {"kind": "record", "key": key, "value": value, "optional": optional}
	if description:
		schema["description"] = description
	return schema


ModelUsageSchema = lazy_schema(
	lambda: _object_schema(
		{
			"inputTokens": {"kind": "number"},
			"outputTokens": {"kind": "number"},
			"cacheReadInputTokens": {"kind": "number"},
			"cacheCreationInputTokens": {"kind": "number"},
			"webSearchRequests": {"kind": "number"},
			"costUSD": {"kind": "number"},
			"contextWindow": {"kind": "number"},
			"maxOutputTokens": {"kind": "number"},
		}
	)
)
OutputFormatTypeSchema = lazy_schema(lambda: {"kind": "literal", "value": "json_schema"})
BaseOutputFormatSchema = lazy_schema(lambda: _object_schema({"type": OutputFormatTypeSchema()}))
JsonSchemaOutputFormatSchema = lazy_schema(
	lambda: _object_schema(
		{
			"type": {"kind": "literal", "value": "json_schema"},
			"schema": _record_schema({"kind": "unknown"}),
		}
	)
)
OutputFormatSchema = lazy_schema(lambda: JsonSchemaOutputFormatSchema())
ApiKeySourceSchema = lazy_schema(lambda: _enum_schema(["user", "project", "org", "temporary", "oauth"]))
ConfigScopeSchema = lazy_schema(lambda: _enum_schema(["local", "user", "project"], description="Config scope for settings."))
SdkBetaSchema = lazy_schema(lambda: {"kind": "literal", "value": "context-1m-2025-08-07"})
ThinkingAdaptiveSchema = lazy_schema(lambda: _object_schema({"type": {"kind": "literal", "value": "adaptive"}}, description="vivian decides when and how much to think (Opus 4.6+)."))
ThinkingEnabledSchema = lazy_schema(lambda: _object_schema({"type": {"kind": "literal", "value": "enabled"}, "budgetTokens": {"kind": "number", "optional": True}}, description="Fixed thinking token budget (older models)"))
ThinkingDisabledSchema = lazy_schema(lambda: _object_schema({"type": {"kind": "literal", "value": "disabled"}}, description="No extended thinking"))
ThinkingConfigSchema = lazy_schema(lambda: {"kind": "union", "variants": [ThinkingAdaptiveSchema(), ThinkingEnabledSchema(), ThinkingDisabledSchema()], "description": "Controls vivian's thinking/reasoning behavior."})
McpStdioServerConfigSchema = lazy_schema(lambda: _object_schema({"type": {"kind": "literal", "value": "stdio", "optional": True}, "command": {"kind": "string"}, "args": _array_schema("string", optional=True), "env": _record_schema("string", optional=True)}))
McpSSEServerConfigSchema = lazy_schema(lambda: _object_schema({"type": {"kind": "literal", "value": "sse"}, "url": {"kind": "string"}, "headers": _record_schema("string", optional=True)}))
McpHttpServerConfigSchema = lazy_schema(lambda: _object_schema({"type": {"kind": "literal", "value": "http"}, "url": {"kind": "string"}, "headers": _record_schema("string", optional=True)}))
McpSdkServerConfigSchema = lazy_schema(lambda: _object_schema({"type": {"kind": "literal", "value": "sdk"}, "name": {"kind": "string"}}))
McpServerConfigForProcessTransportSchema = lazy_schema(lambda: {"kind": "union", "variants": [McpStdioServerConfigSchema(), McpSSEServerConfigSchema(), McpHttpServerConfigSchema(), McpSdkServerConfigSchema()]})
McpvivianAIProxyServerConfigSchema = lazy_schema(lambda: _object_schema({"type": {"kind": "literal", "value": "vivianai-proxy"}, "url": {"kind": "string"}, "id": {"kind": "string"}}))
McpServerStatusConfigSchema = lazy_schema(lambda: {"kind": "union", "variants": [McpServerConfigForProcessTransportSchema(), McpvivianAIProxyServerConfigSchema()]})
McpServerStatusSchema = lazy_schema(
	lambda: _object_schema(
		{
			"name": {"kind": "string"},
			"status": _enum_schema(["connected", "failed", "needs-auth", "pending", "disabled"]),
			"serverInfo": {"kind": "object", "properties": {"name": {"kind": "string"}, "version": {"kind": "string"}}, "optional": True},
			"error": {"kind": "string", "optional": True},
			"config": {**McpServerStatusConfigSchema(), "optional": True},
			"scope": {"kind": "string", "optional": True},
			"tools": _array_schema(_object_schema({"name": {"kind": "string"}, "description": {"kind": "string", "optional": True}, "annotations": {"kind": "object", "properties": {"readOnly": {"kind": "boolean", "optional": True}, "destructive": {"kind": "boolean", "optional": True}, "openWorld": {"kind": "boolean", "optional": True}}, "optional": True}}), optional=True),
			"capabilities": {"kind": "object", "properties": {"experimental": _record_schema({"kind": "unknown"}, optional=True)}, "optional": True},
		},
		description="Status information for an MCP server connection.",
	)
)
McpSetServersResultSchema = lazy_schema(lambda: _object_schema({"added": _array_schema("string"), "removed": _array_schema("string"), "errors": _record_schema("string")}, description="Result of a setMcpServers operation."))
PermissionUpdateDestinationSchema = lazy_schema(lambda: _enum_schema(["userSettings", "projectSettings", "localSettings", "session", "cliArg"]))
PermissionBehaviorSchema = lazy_schema(lambda: _enum_schema(["allow", "deny", "ask"]))
PermissionRuleValueSchema = lazy_schema(lambda: _object_schema({"toolName": {"kind": "string"}, "ruleContent": {"kind": "string", "optional": True}}))
PermissionModeSchema = lazy_schema(lambda: _enum_schema(list(EXTERNAL_PERMISSION_MODES), description="Permission mode for controlling how tool executions are handled."))
PermissionUpdateSchema = lazy_schema(
	lambda: {
		"kind": "discriminatedUnion",
		"tag": "type",
		"variants": [
			_object_schema({"type": {"kind": "literal", "value": "addRules"}, "rules": _array_schema(PermissionRuleValueSchema()), "behavior": PermissionBehaviorSchema(), "destination": PermissionUpdateDestinationSchema()}),
			_object_schema({"type": {"kind": "literal", "value": "replaceRules"}, "rules": _array_schema(PermissionRuleValueSchema()), "behavior": PermissionBehaviorSchema(), "destination": PermissionUpdateDestinationSchema()}),
			_object_schema({"type": {"kind": "literal", "value": "removeRules"}, "rules": _array_schema(PermissionRuleValueSchema()), "behavior": PermissionBehaviorSchema(), "destination": PermissionUpdateDestinationSchema()}),
			_object_schema({"type": {"kind": "literal", "value": "setMode"}, "mode": PermissionModeSchema(), "destination": PermissionUpdateDestinationSchema()}),
			_object_schema({"type": {"kind": "literal", "value": "addDirectories"}, "directories": _array_schema("string"), "destination": PermissionUpdateDestinationSchema()}),
			_object_schema({"type": {"kind": "literal", "value": "removeDirectories"}, "directories": _array_schema("string"), "destination": PermissionUpdateDestinationSchema()}),
		],
	}
)
PermissionDecisionClassificationSchema = lazy_schema(lambda: _enum_schema(["user_temporary", "user_permanent", "user_reject"]))
PermissionResultSchema = lazy_schema(
	lambda: {
		"kind": "union",
		"variants": [
			_object_schema({"behavior": {"kind": "literal", "value": "allow"}, "updatedInput": _record_schema({"kind": "unknown"}, optional=True), "updatedPermissions": _array_schema(PermissionUpdateSchema(), optional=True), "toolUseID": {"kind": "string", "optional": True}, "decisionClassification": {**PermissionDecisionClassificationSchema(), "optional": True}}),
			_object_schema({"behavior": {"kind": "literal", "value": "deny"}, "message": {"kind": "string"}, "interrupt": {"kind": "boolean", "optional": True}, "toolUseID": {"kind": "string", "optional": True}, "decisionClassification": {**PermissionDecisionClassificationSchema(), "optional": True}}),
		],
	}
)
HookEventSchema = lazy_schema(lambda: _enum_schema(HOOK_EVENTS))
BaseHookInputSchema = lazy_schema(lambda: _object_schema({"session_id": {"kind": "string"}, "transcript_path": {"kind": "string"}, "cwd": {"kind": "string"}, "permission_mode": {"kind": "string", "optional": True}, "agent_id": {"kind": "string", "optional": True}, "agent_type": {"kind": "string", "optional": True}}))
PreToolUseHookInputSchema = lazy_schema(lambda: {"kind": "intersection", "variants": [BaseHookInputSchema(), _object_schema({"hook_event_name": {"kind": "literal", "value": "PreToolUse"}, "tool_name": {"kind": "string"}, "tool_input": {"kind": "unknown"}, "tool_use_id": {"kind": "string"}})]})
PermissionRequestHookInputSchema = lazy_schema(lambda: {"kind": "intersection", "variants": [BaseHookInputSchema(), _object_schema({"hook_event_name": {"kind": "literal", "value": "PermissionRequest"}, "tool_name": {"kind": "string"}, "tool_input": {"kind": "unknown"}, "permission_suggestions": _array_schema(PermissionUpdateSchema(), optional=True)})]})
PostToolUseHookInputSchema = lazy_schema(lambda: {"kind": "intersection", "variants": [BaseHookInputSchema(), _object_schema({"hook_event_name": {"kind": "literal", "value": "PostToolUse"}, "tool_name": {"kind": "string"}, "tool_input": {"kind": "unknown"}, "tool_response": {"kind": "unknown"}, "tool_use_id": {"kind": "string"}})]})
PostToolUseFailureHookInputSchema = lazy_schema(lambda: {"kind": "intersection", "variants": [BaseHookInputSchema(), _object_schema({"hook_event_name": {"kind": "literal", "value": "PostToolUseFailure"}, "tool_name": {"kind": "string"}, "tool_input": {"kind": "unknown"}, "tool_use_id": {"kind": "string"}, "error": {"kind": "string"}, "is_interrupt": {"kind": "boolean", "optional": True}})]})
PermissionDeniedHookInputSchema = lazy_schema(lambda: {"kind": "intersection", "variants": [BaseHookInputSchema(), _object_schema({"hook_event_name": {"kind": "literal", "value": "PermissionDenied"}, "tool_name": {"kind": "string"}, "tool_input": {"kind": "unknown"}, "tool_use_id": {"kind": "string"}, "reason": {"kind": "string"}})]})
NotificationHookInputSchema = lazy_schema(lambda: {"kind": "intersection", "variants": [BaseHookInputSchema(), _object_schema({"hook_event_name": {"kind": "literal", "value": "Notification"}, "message": {"kind": "string"}, "title": {"kind": "string", "optional": True}, "notification_type": {"kind": "string"}})]})
UserPromptSubmitHookInputSchema = lazy_schema(lambda: {"kind": "intersection", "variants": [BaseHookInputSchema(), _object_schema({"hook_event_name": {"kind": "literal", "value": "UserPromptSubmit"}, "prompt": {"kind": "string"}})]})
SessionStartHookInputSchema = lazy_schema(lambda: {"kind": "intersection", "variants": [BaseHookInputSchema(), _object_schema({"hook_event_name": {"kind": "literal", "value": "SessionStart"}, "source": _enum_schema(["startup", "resume", "clear", "compact"]), "agent_type": {"kind": "string", "optional": True}, "model": {"kind": "string", "optional": True}})]})
SetupHookInputSchema = lazy_schema(lambda: {"kind": "intersection", "variants": [BaseHookInputSchema(), _object_schema({"hook_event_name": {"kind": "literal", "value": "Setup"}, "trigger": _enum_schema(["init", "maintenance"])})]})
StopHookInputSchema = lazy_schema(lambda: {"kind": "intersection", "variants": [BaseHookInputSchema(), _object_schema({"hook_event_name": {"kind": "literal", "value": "Stop"}, "stop_hook_active": {"kind": "boolean"}, "last_assistant_message": {"kind": "string", "optional": True}})]})

CoreSchemas = dict[str, Any]

__all__ = [name for name in list(globals()) if name.endswith("Schema") or name in {"CoreSchemas", "HOOK_EVENTS"}]
