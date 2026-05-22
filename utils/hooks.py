"""
passpasspasspass of src/utils/hooks
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

from ..bootstrap.state import (
    getIsNonInteractiveSession,
    getMainThreadAgentType,
    getSessionId,
    getSessionTrustAccepted,
)
from ..types.hooks import HookJSONOutput
from .debug import logForDebugging


SESSION_END_HOOK_TIMEOUT_MS_DEFAULT = 1500
_HOOK_OUTPUT_SCHEMA_HINT = json.dumps(
    {
        "continue": "boolean (optional)",
        "suppressOutput": "boolean (optional)",
        "stopReason": "string (optional)",
        "decision": '"approve" | "block" (optional)',
        "reason": "string (optional)",
        "systemMessage": "string (optional)",
        "permissionDecision": '"allow" | "deny" | "ask" (optional)',
        "hookSpecificOutput": {
            "for PreToolUse": {
                "hookEventName": '"PreToolUse"',
                "permissionDecision": '"allow" | "deny" | "ask" (optional)',
                "permissionDecisionReason": "string (optional)",
                "updatedInput": "object (optional) - Modified tool input to use",
            },
            "for UserPromptSubmit": {
                "hookEventName": '"UserPromptSubmit"',
                "additionalContext": "string (required)",
            },
            "for PostToolUse": {
                "hookEventName": '"PostToolUse"',
                "additionalContext": "string (optional)",
            },
        },
    },
    indent=2,
)

ElicitationResponse = Any
AggregatedHookResult = Dict[str, Any]


class HookBlockingError(TypedDict, total=False):
    blockingError: str
    command: str


class HookResult(TypedDict, total=False):
    message: Any
    systemMessage: str
    blockingError: HookBlockingError
    outcome: str
    preventContinuation: bool
    stopReason: str
    permissionBehavior: str
    hookPermissionDecisionReason: str
    additionalContext: str
    initialUserMessage: str
    updatedInput: Dict[str, Any]
    updatedMCPToolOutput: Any
    permissionRequestResult: Any
    elicitationResponse: ElicitationResponse
    watchPaths: List[str]
    elicitationResultResponse: ElicitationResponse
    retry: bool
    hook: Any


def getSessionEndHookTimeoutMs():
    raw = os.environ.get("vivian_CODE_SESSIONEND_HOOKS_TIMEOUT_MS")
    try:
        parsed = int(raw) if raw is not None else math.nan
    except (TypeError, ValueError):
        parsed = math.nan
    if isinstance(parsed, int) and parsed > 0:
        return parsed
    return SESSION_END_HOOK_TIMEOUT_MS_DEFAULT


def executeInBackground(__processId__hookId__shellCommand__asyncResponse__hookEvent__hookName__command__asyncRewake__pluginId___=None):
    result = None
    _input = __processId__hookId__shellCommand__asyncResponse__hookEvent__hookName__command__asyncRewake__pluginId___
    _output = _input if _input is not None else {}
    return _output


def shouldSkipHookDueToTrust():
    """Checks if a hook should be skipped due to lack of workspace trust."""
    if getIsNonInteractiveSession():
        return False
    return not getSessionTrustAccepted()


def createBaseHookInput(permissionMode=None, sessionId=None, ___Typed_narrowly__not_ToolUseContext__so_callers_can_pass_toolUseContext____directly_via_structural_typing_without_this_function_depending_on_Tool_ts__agentInfo=None):
    """Creates the base hook input that's common to all hook types"""
    from ..constants.system import getCwd
    from .sessionStorage import getTranscriptPathForSession

    agent_info = (
        ___Typed_narrowly__not_ToolUseContext__so_callers_can_pass_toolUseContext____directly_via_structural_typing_without_this_function_depending_on_Tool_ts__agentInfo
        or {}
    )
    resolved_session_id = sessionId or getSessionId()
    resolved_agent_type = agent_info.get("agentType") or getMainThreadAgentType()
    try:
        transcript_path = getTranscriptPathForSession(resolved_session_id)
    except Exception:
        transcript_path = str(Path(getCwd()) / f"{resolved_session_id}.jsonl")
    return {
        "session_id": resolved_session_id,
        "transcript_path": transcript_path,
        "cwd": getCwd(),
        "permission_mode": permissionMode,
        "agent_id": agent_info.get("agentId"),
        "agent_type": resolved_agent_type,
    }


def validateHookJson(jsonString):
    """Parse and validate a JSON string against the hook output Zod schema."""
    parsed = json.loads(jsonString)
    if not isinstance(parsed, dict):
        return {"validationError": "Hook JSON output validation failed:\n  - : expected top-level object"}

    allowed_keys = {
        "async",
        "continue",
        "suppressOutput",
        "stopReason",
        "decision",
        "reason",
        "systemMessage",
        "permissionDecision",
        "hookSpecificOutput",
    }
    invalid_keys = sorted(key for key in parsed if key not in allowed_keys)
    if invalid_keys:
        errors = "\n".join(f"  - {key}: unexpected field" for key in invalid_keys)
        return {
            "validationError": (
                "Hook JSON output validation failed:\n"
                f"{errors}\n\nThe hook's output was: {json.dumps(parsed, indent=2)}"
            )
        }

    if "async" in parsed and not isinstance(parsed["async"], bool):
        return {
            "validationError": (
                "Hook JSON output validation failed:\n"
                "  - async: expected boolean\n\n"
                f"The hook's output was: {json.dumps(parsed, indent=2)}"
            )
        }

    if parsed.get("async") is True:
        logForDebugging("Successfully parsed and validated hook JSON output")
        return {"json": parsed}

    typed_fields = {
        "continue": bool,
        "suppressOutput": bool,
        "stopReason": str,
        "decision": str,
        "reason": str,
        "systemMessage": str,
        "permissionDecision": str,
    }
    issues: List[str] = []
    for field_name, field_type in typed_fields.items():
        if field_name in parsed and parsed[field_name] is not None and not isinstance(parsed[field_name], field_type):
            issues.append(f"  - {field_name}: expected {field_type.__name__}")
    if "hookSpecificOutput" in parsed and parsed["hookSpecificOutput"] is not None and not isinstance(parsed["hookSpecificOutput"], dict):
        issues.append("  - hookSpecificOutput: expected object")
    if parsed.get("decision") not in (None, "approve", "block"):
        issues.append("  - decision: expected approve or block")
    if parsed.get("permissionDecision") not in (None, "allow", "deny", "ask"):
        issues.append("  - permissionDecision: expected allow, deny, or ask")
    if issues:
        return {
            "validationError": (
                "Hook JSON output validation failed:\n"
                f"{'\n'.join(issues)}\n\nThe hook's output was: {json.dumps(parsed, indent=2)}"
            )
        }

    logForDebugging("Successfully parsed and validated hook JSON output")
    return {"json": parsed}


def parseHookOutput(stdout):
    trimmed = stdout.strip()
    if not trimmed.startswith("{"):
        logForDebugging("Hook output does not start with {, treating as plain text")
        return {"plainText": stdout}

    try:
        result = validateHookJson(trimmed)
        if "json" in result:
            return result
        error_message = f"{result['validationError']}\n\nExpected schema:\n{_HOOK_OUTPUT_SCHEMA_HINT}"
        logForDebugging(error_message)
        return {"plainText": stdout, "validationError": error_message}
    except Exception as error:
        logForDebugging(f"Failed to parse hook output as JSON: {error}")
        return {"plainText": stdout}


get_session_end_hook_timeout_ms = getSessionEndHookTimeoutMs
should_skip_hook_due_to_trust = shouldSkipHookDueToTrust
create_base_hook_input = createBaseHookInput
validate_hook_json = validateHookJson
parse_hook_output = parseHookOutput


def _get_snapshot_hooks(event_name: str) -> list[dict[str, Any]]:
    try:
        from .hooks.hooksConfigSnapshot import get_hooks_config_from_snapshot
        config = get_hooks_config_from_snapshot() or {}
    except Exception:
        config = {}
    value = config.get(event_name, [])
    return value if isinstance(value, list) else []


def _matcher_value(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    return "" if value is None else str(value)


def _matcher_matches(matcher: Any, payload: dict[str, Any]) -> bool:
    if matcher in (None, "", "*"):
        return True
    if isinstance(matcher, dict):
        field = matcher.get("fieldToMatch") or matcher.get("field")
        value = matcher.get("value")
        if field and value is not None:
            return _matcher_value(payload, str(field)) == str(value)
        pattern = matcher.get("pattern")
        if isinstance(pattern, str):
            target = payload.get("path") or payload.get("notification_type") or ""
            return pattern in str(target)
    if isinstance(matcher, str):
        candidate = str(payload.get("path") or payload.get("notification_type") or "")
        return matcher == candidate or matcher in candidate
    return True


def _iter_matching_hooks(event_name: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    matched: list[dict[str, Any]] = []
    for entry in _get_snapshot_hooks(event_name):
        if not isinstance(entry, dict):
            continue
        if not _matcher_matches(entry.get("matcher"), payload):
            continue
        hooks = entry.get("hooks") or []
        if isinstance(hooks, list):
            matched.extend(hook for hook in hooks if isinstance(hook, dict))
    return matched


async def _run_shell_hook(hook: dict[str, Any], payload_json: str) -> HookResult:
    command = hook.get("command")
    if not isinstance(command, str) or not command.strip():
        return {"hook": hook, "outcome": "non_blocking_error", "blockingError": {"blockingError": "Hook command is empty", "command": ""}}

    env = dict(os.environ)
    env["vivian_HOOK_INPUT"] = payload_json
    env.setdefault("vivian_HOOK_SESSION_ID", getSessionId())

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout_b, stderr_b = await proc.communicate(payload_json.encode("utf-8"))
    except Exception as exc:
        return {"hook": hook, "outcome": "non_blocking_error", "blockingError": {"blockingError": str(exc), "command": command}}

    stdout = stdout_b.decode("utf-8", errors="replace")
    stderr = stderr_b.decode("utf-8", errors="replace")
    parsed = parseHookOutput(stdout)

    if proc.returncode == 0:
        return {
            "hook": hook,
            "outcome": "success",
            "message": stdout.strip() or None,
            "systemMessage": (parsed.get("json") or {}).get("systemMessage") if isinstance(parsed, dict) else None,
        }
    if proc.returncode == 2:
        return {
            "hook": hook,
            "outcome": "blocking",
            "blockingError": {
                "blockingError": stderr.strip() or stdout.strip() or "Hook blocked continuation",
                "command": command,
            },
            "preventContinuation": True,
            "stopReason": stderr.strip() or stdout.strip() or "Hook blocked continuation",
        }
    return {
        "hook": hook,
        "outcome": "non_blocking_error",
        "blockingError": {
            "blockingError": stderr.strip() or stdout.strip() or f"Hook failed with exit code {proc.returncode}",
            "command": command,
        },
    }


async def _execute_hook(hook: dict[str, Any], event_name: str, payload: dict[str, Any]) -> HookResult:
    hook_type = str(hook.get("type") or "command")
    payload_json = json.dumps(payload, ensure_ascii=False)

    if hook_type == "http":
        from .hooks.execHttpHook import exec_http_hook
        result = await exec_http_hook(hook, event_name, payload_json)
        return {"hook": hook, "outcome": "success" if result.get("ok") else "non_blocking_error", "message": result.get("body")}
    if hook_type == "prompt":
        from .hooks.execPromptHook import exec_prompt_hook
        return await exec_prompt_hook(hook, str(hook.get("command") or hook.get("prompt") or event_name), event_name, payload_json, None, None)
    return await _run_shell_hook(hook, payload_json)


async def _execute_event_hooks(event_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for hook in _iter_matching_hooks(event_name, payload):
        result = await _execute_hook(hook, event_name, payload)
        results.append(
            {
                "hook": hook,
                "succeeded": result.get("outcome") == "success",
                "outcome": result.get("outcome"),
                "output": result.get("message") or result.get("systemMessage") or (result.get("blockingError") or {}).get("blockingError"),
                "result": result,
            }
        )
    return {"results": results}


async def execute_notification_hooks(notification: dict[str, Any]) -> dict[str, Any]:
    payload = dict(notification or {})
    payload.setdefault("notification_type", payload.get("type") or payload.get("channel") or "generic")
    return await _execute_event_hooks("Notification", payload)


async def execute_file_changed_hooks(path: str, event: str) -> dict[str, Any]:
    return await _execute_event_hooks("FileChanged", {"path": path, "event": event})


class _HooksFacade:
    async def execute_file_changed_hooks(self, path: str, event: str) -> dict[str, Any]:
        return await execute_file_changed_hooks(path, event)

    async def execute_notification_hooks(self, notification: dict[str, Any]) -> dict[str, Any]:
        return await execute_notification_hooks(notification)


hooks = _HooksFacade()

execute_notification_hooks = execute_notification_hooks

