"""SDK control schemas.

Python port of src/entrypoints/sdk/controlSchemas.ts.
"""
from __future__ import annotations

from typing import Any

from ...utils.lazySchema import lazy_schema
from .coreSchemas import HookEventSchema, McpServerConfigForProcessTransportSchema, McpServerStatusSchema, PermissionModeSchema, PermissionUpdateSchema


def _object_schema(properties: dict[str, Any], *, description: str | None = None) -> dict[str, Any]:
	schema = {"kind": "object", "properties": properties}
	if description:
		schema["description"] = description
	return schema


def _array_schema(items: Any, *, optional: bool = False) -> dict[str, Any]:
	return {"kind": "array", "items": items, "optional": optional}


def _record_schema(value: Any, *, key: Any = "string", optional: bool = False) -> dict[str, Any]:
	return {"kind": "record", "key": key, "value": value, "optional": optional}


JSONRPCMessagePlaceholder = lazy_schema(lambda: {"kind": "unknown"})
SDKHookCallbackMatcherSchema = lazy_schema(lambda: _object_schema({"matcher": {"kind": "string", "optional": True}, "hookCallbackIds": _array_schema("string"), "timeout": {"kind": "number", "optional": True}}, description="Configuration for matching and routing hook callbacks."))
SDKControlInitializeRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "initialize"}, "hooks": _record_schema(_array_schema(SDKHookCallbackMatcherSchema()), key=HookEventSchema(), optional=True), "sdkMcpServers": _array_schema("string", optional=True), "jsonSchema": _record_schema({"kind": "unknown"}, optional=True), "systemPrompt": {"kind": "string", "optional": True}, "appendSystemPrompt": {"kind": "string", "optional": True}, "agents": _record_schema({"kind": "unknown"}, optional=True), "promptSuggestions": {"kind": "boolean", "optional": True}, "agentProgressSummaries": {"kind": "boolean", "optional": True}}, description="Initializes the SDK session with hooks, MCP servers, and agent configuration."))
SDKControlInitializeResponseSchema = lazy_schema(lambda: _object_schema({"commands": _array_schema({"kind": "unknown"}), "agents": _array_schema({"kind": "unknown"}), "output_style": {"kind": "string"}, "available_output_styles": _array_schema("string"), "models": _array_schema({"kind": "unknown"}), "account": {"kind": "unknown"}, "pid": {"kind": "number", "optional": True}, "fast_mode_state": {"kind": "unknown", "optional": True}}))
SDKControlInterruptRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "interrupt"}}, description="Interrupts the currently running conversation turn."))
SDKControlPermissionRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "can_use_tool"}, "tool_name": {"kind": "string"}, "input": _record_schema({"kind": "unknown"}), "permission_suggestions": _array_schema(PermissionUpdateSchema(), optional=True), "blocked_path": {"kind": "string", "optional": True}, "decision_reason": {"kind": "string", "optional": True}, "title": {"kind": "string", "optional": True}, "display_name": {"kind": "string", "optional": True}, "tool_use_id": {"kind": "string"}, "agent_id": {"kind": "string", "optional": True}, "description": {"kind": "string", "optional": True}}, description="Requests permission to use a tool with the given input."))
SDKControlSetPermissionModeRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "set_permission_mode"}, "mode": PermissionModeSchema(), "ultraplan": {"kind": "boolean", "optional": True}}, description="Sets the permission mode for tool execution handling."))
SDKControlSetModelRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "set_model"}, "model": {"kind": "string", "optional": True}}, description="Sets the model to use for subsequent conversation turns."))
SDKControlSetMaxThinkingTokensRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "set_max_thinking_tokens"}, "max_thinking_tokens": {"kind": "number", "nullable": True}}, description="Sets the maximum number of thinking tokens for extended thinking."))
SDKControlMcpStatusRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "mcp_status"}}))
SDKControlMcpStatusResponseSchema = lazy_schema(lambda: _object_schema({"mcpServers": _array_schema(McpServerStatusSchema())}))
SDKControlGetContextUsageRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "get_context_usage"}}))
SDKControlGetContextUsageResponseSchema = lazy_schema(lambda: _object_schema({"categories": _array_schema({"kind": "unknown"}), "totalTokens": {"kind": "number"}, "maxTokens": {"kind": "number"}, "rawMaxTokens": {"kind": "number"}, "percentage": {"kind": "number"}, "gridRows": _array_schema(_array_schema({"kind": "unknown"})), "model": {"kind": "string"}, "memoryFiles": _array_schema(_object_schema({"path": {"kind": "string"}, "type": {"kind": "string"}, "tokens": {"kind": "number"}})), "mcpTools": _array_schema(_object_schema({"name": {"kind": "string"}, "serverName": {"kind": "string"}, "tokens": {"kind": "number"}, "isLoaded": {"kind": "boolean", "optional": True}})), "deferredBuiltinTools": _array_schema(_object_schema({"name": {"kind": "string"}, "tokens": {"kind": "number"}, "isLoaded": {"kind": "boolean"}}), optional=True), "systemTools": _array_schema(_object_schema({"name": {"kind": "string"}, "tokens": {"kind": "number"}}), optional=True), "systemPromptSections": _array_schema(_object_schema({"name": {"kind": "string"}, "tokens": {"kind": "number"}}), optional=True), "agents": _array_schema(_object_schema({"agentType": {"kind": "string"}, "source": {"kind": "string"}, "tokens": {"kind": "number"}})), "autoCompactThreshold": {"kind": "number", "optional": True}, "isAutoCompactEnabled": {"kind": "boolean"}, "apiUsage": {"kind": "object", "properties": {"input_tokens": {"kind": "number"}, "output_tokens": {"kind": "number"}, "cache_creation_input_tokens": {"kind": "number"}, "cache_read_input_tokens": {"kind": "number"}}, "nullable": True}}))
SDKControlRewindFilesRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "rewind_files"}, "user_message_id": {"kind": "string"}, "dry_run": {"kind": "boolean", "optional": True}}))
SDKControlRewindFilesResponseSchema = lazy_schema(lambda: _object_schema({"canRewind": {"kind": "boolean"}, "error": {"kind": "string", "optional": True}, "filesChanged": _array_schema("string", optional=True), "insertions": {"kind": "number", "optional": True}, "deletions": {"kind": "number", "optional": True}}))
SDKControlCancelAsyncMessageRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "cancel_async_message"}, "message_uuid": {"kind": "string"}}))
SDKControlCancelAsyncMessageResponseSchema = lazy_schema(lambda: _object_schema({"cancelled": {"kind": "boolean"}}))
SDKControlSeedReadStateRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "seed_read_state"}, "path": {"kind": "string"}, "mtime": {"kind": "number"}}))
SDKHookCallbackRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "hook_callback"}, "callback_id": {"kind": "string"}, "input": {"kind": "unknown"}, "tool_use_id": {"kind": "string", "optional": True}}))
SDKControlMcpMessageRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "mcp_message"}, "server_name": {"kind": "string"}, "message": JSONRPCMessagePlaceholder()}))
SDKControlMcpSetServersRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "mcp_set_servers"}, "servers": _record_schema(McpServerConfigForProcessTransportSchema())}))
SDKControlMcpSetServersResponseSchema = lazy_schema(lambda: _object_schema({"added": _array_schema("string"), "removed": _array_schema("string"), "errors": _record_schema("string")}))
SDKControlReloadPluginsRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "reload_plugins"}}))
SDKControlReloadPluginsResponseSchema = lazy_schema(lambda: _object_schema({"commands": _array_schema({"kind": "unknown"}), "agents": _array_schema({"kind": "unknown"}), "plugins": _array_schema(_object_schema({"name": {"kind": "string"}, "path": {"kind": "string"}, "source": {"kind": "string", "optional": True}})), "mcpServers": _array_schema(McpServerStatusSchema()), "error_count": {"kind": "number"}}))
SDKControlMcpReconnectRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "mcp_reconnect"}, "serverName": {"kind": "string"}}))
SDKControlMcpToggleRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "mcp_toggle"}, "serverName": {"kind": "string"}, "enabled": {"kind": "boolean"}}))
SDKControlStopTaskRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "stop_task"}, "task_id": {"kind": "string"}}))
SDKControlApplyFlagSettingsRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "apply_flag_settings"}, "settings": _record_schema({"kind": "unknown"})}))
SDKControlGetSettingsRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "get_settings"}}))
SDKControlGetSettingsResponseSchema = lazy_schema(lambda: _object_schema({"effective": _record_schema({"kind": "unknown"}), "sources": _array_schema(_object_schema({"source": {"kind": "enum", "values": ["userSettings", "projectSettings", "localSettings", "flagSettings", "policySettings"]}, "settings": _record_schema({"kind": "unknown"})})), "applied": {"kind": "object", "properties": {"model": {"kind": "string"}, "effort": {"kind": "enum", "values": ["low", "medium", "high", "max"], "nullable": True}}, "optional": True}}))
SDKControlElicitationRequestSchema = lazy_schema(lambda: _object_schema({"subtype": {"kind": "literal", "value": "elicitation"}, "mcp_server_name": {"kind": "string"}, "message": {"kind": "string"}, "mode": {"kind": "enum", "values": ["form", "url"], "optional": True}, "url": {"kind": "string", "optional": True}, "elicitation_id": {"kind": "string", "optional": True}, "requested_schema": _record_schema({"kind": "unknown"}, optional=True)}))

ControlSchemas = dict[str, Any]

__all__ = [name for name in list(globals()) if name.endswith("Schema") or name == "ControlSchemas"]
