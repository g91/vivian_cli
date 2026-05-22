"""Port of src/utils/telemetry/betaSessionTracing.ts."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from typing import Any, TypedDict

from ...bootstrap.state import getIsNonInteractiveSession
from ..envUtils import is_env_truthy

try:
    from .events import logOTelEvent
except Exception:  # pragma: no cover - optional while events.py is unfinished
    logOTelEvent = None


APIMessage = dict[str, Any]
MAX_CONTENT_SIZE = 60 * 1024
SYSTEM_REMINDER_REGEX = re.compile(r"^<system-reminder>\n?([\s\S]*?)\n?</system-reminder>$")
seenHashes: set[str] = set()
lastReportedMessageHash: dict[str, str] = {}


class FormattedMessages(TypedDict, total=False):
    """Result of formatting messages - separates regular content from system reminders."""

    contextParts: list[str]
    systemReminders: list[str]


class LLMRequestNewContext(TypedDict, total=False):
    systemPrompt: str
    querySource: str
    tools: str


def _safe_json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _set_span_attributes(span: Any, attrs: dict[str, Any]) -> None:
    if not attrs:
        return
    if hasattr(span, "setAttributes"):
        span.setAttributes(attrs)
        return
    for key, value in attrs.items():
        if hasattr(span, "setAttribute"):
            span.setAttribute(key, value)


def _get_message_content(message: APIMessage) -> Any:
    if not isinstance(message, dict):
        return None
    if isinstance(message.get("message"), dict):
        return message["message"].get("content")
    return message.get("content")


def _get_message_type(message: APIMessage) -> str | None:
    if not isinstance(message, dict):
        return None
    return message.get("type") or (message.get("message") or {}).get("role")


def _sanitize_tool_name(tool_name: Any) -> str:
    value = str(tool_name or "unknown")
    return re.sub(r"[^a-zA-Z0-9_.:-]", "_", value)


def _log_event_fire_and_forget(event_name: str, metadata: dict[str, Any]) -> None:
    if logOTelEvent is None:
        return
    try:
        result = logOTelEvent(event_name, metadata)
    except Exception:
        return
    if asyncio.iscoroutine(result):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            result.close()
            return
        loop.create_task(result)


def clearBetaTracingState():
    """Clear tracking state after compaction."""
    seenHashes.clear()
    lastReportedMessageHash.clear()


def isBetaTracingEnabled():
    """Check if beta detailed tracing is enabled."""
    base_enabled = is_env_truthy(os.environ.get("ENABLE_BETA_TRACING_DETAILED")) and bool(
        os.environ.get("BETA_TRACING_ENDPOINT")
    )
    if not base_enabled:
        return False
    if os.environ.get("USER_TYPE") != "ant":
        return getIsNonInteractiveSession()
    return True


def truncateContent(content, maxSize=MAX_CONTENT_SIZE):
    """Truncate content to fit within Honeycomb limits."""
    if len(content) <= maxSize:
        return {"content": content, "truncated": False}
    return {
        "content": content[:maxSize] + "\n\n[TRUNCATED - Content exceeds 60KB limit]",
        "truncated": True,
    }


def shortHash(content):
    """Generate a short hash (first 12 hex chars of SHA-256)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]


def hashSystemPrompt(systemPrompt):
    """Generate a hash for a system prompt."""
    return f"sp_{shortHash(systemPrompt)}"


def hashMessage(message):
    """Generate a hash for a message based on its content."""
    return f"msg_{shortHash(_safe_json_dumps(_get_message_content(message)))}"


def extractSystemReminderContent(text):
    """Check if text is entirely a system reminder (wrapped in tags)."""
    match = SYSTEM_REMINDER_REGEX.match(str(text).strip())
    return match.group(1).strip() if match and match.group(1) else None


def formatMessagesForContext(messages):
    """Format user messages for new_context display, separating system reminders."""
    context_parts: list[str] = []
    system_reminders: list[str] = []

    for message in messages or []:
        content = _get_message_content(message)
        if isinstance(content, str):
            reminder = extractSystemReminderContent(content)
            if reminder:
                system_reminders.append(reminder)
            else:
                context_parts.append(f"[USER]\n{content}")
            continue

        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    text = str(block.get("text") or "")
                    reminder = extractSystemReminderContent(text)
                    if reminder:
                        system_reminders.append(reminder)
                    else:
                        context_parts.append(f"[USER]\n{text}")
                elif block.get("type") == "tool_result":
                    raw_result = block.get("content")
                    result_content = raw_result if isinstance(raw_result, str) else _safe_json_dumps(raw_result)
                    reminder = extractSystemReminderContent(result_content)
                    if reminder:
                        system_reminders.append(reminder)
                    else:
                        context_parts.append(
                            f"[TOOL RESULT: {block.get('tool_use_id', 'unknown')}]\n{result_content}"
                        )

    return {"contextParts": context_parts, "systemReminders": system_reminders}


def addBetaInteractionAttributes(span, userPrompt):
    """Add beta attributes to an interaction span."""
    if not isBetaTracingEnabled():
        return
    truncated = truncateContent(f"[USER PROMPT]\n{userPrompt}")
    attrs = {"new_context": truncated["content"]}
    if truncated["truncated"]:
        attrs["new_context_truncated"] = True
        attrs["new_context_original_length"] = len(userPrompt)
    _set_span_attributes(span, attrs)


def addBetaLLMRequestAttributes(span, newContext=None, messagesForAPI=None):
    """Add beta attributes to an LLM request span."""
    if not isBetaTracingEnabled():
        return

    newContext = newContext or {}
    if newContext.get("systemPrompt"):
        system_prompt = str(newContext["systemPrompt"])
        prompt_hash = hashSystemPrompt(system_prompt)
        _set_span_attributes(
            span,
            {
                "system_prompt_hash": prompt_hash,
                "system_prompt_preview": system_prompt[:500],
                "system_prompt_length": len(system_prompt),
            },
        )

        if prompt_hash not in seenHashes:
            seenHashes.add(prompt_hash)
            truncated = truncateContent(system_prompt)
            _log_event_fire_and_forget(
                "system_prompt",
                {
                    "system_prompt_hash": prompt_hash,
                    "system_prompt": truncated["content"],
                    "system_prompt_length": str(len(system_prompt)),
                    **({"system_prompt_truncated": "true"} if truncated["truncated"] else {}),
                },
            )

    if newContext.get("tools"):
        try:
            tools_array = json.loads(newContext["tools"])
            tools_with_hashes: list[dict[str, str]] = []
            for tool in tools_array:
                tool_json = _safe_json_dumps(tool)
                tool_hash = shortHash(tool_json)
                name = tool.get("name") if isinstance(tool, dict) else "unknown"
                tools_with_hashes.append({"name": str(name), "hash": tool_hash, "json": tool_json})

            _set_span_attributes(
                span,
                {
                    "tools": _safe_json_dumps(
                        [{"name": item["name"], "hash": item["hash"]} for item in tools_with_hashes]
                    ),
                    "tools_count": len(tools_with_hashes),
                },
            )

            for item in tools_with_hashes:
                seen_key = f"tool_{item['hash']}"
                if seen_key in seenHashes:
                    continue
                seenHashes.add(seen_key)
                truncated = truncateContent(item["json"])
                _log_event_fire_and_forget(
                    "tool",
                    {
                        "tool_name": _sanitize_tool_name(item["name"]),
                        "tool_hash": item["hash"],
                        "tool": truncated["content"],
                        **({"tool_truncated": "true"} if truncated["truncated"] else {}),
                    },
                )
        except Exception:
            _set_span_attributes(span, {"tools_parse_error": True})

    query_source = newContext.get("querySource")
    if not query_source or not messagesForAPI:
        return

    last_hash = lastReportedMessageHash.get(query_source)
    start_index = 0
    if last_hash:
        for index, msg in enumerate(messagesForAPI):
            if hashMessage(msg) == last_hash:
                start_index = index + 1
                break

    new_messages = [msg for msg in messagesForAPI[start_index:] if _get_message_type(msg) == "user"]
    if not new_messages:
        return

    formatted = formatMessagesForContext(new_messages)
    context_parts = formatted.get("contextParts") or []
    system_reminders = formatted.get("systemReminders") or []
    attrs: dict[str, Any] = {}

    if context_parts:
        full_context = "\n\n---\n\n".join(context_parts)
        truncated = truncateContent(full_context)
        attrs["new_context"] = truncated["content"]
        attrs["new_context_message_count"] = len(new_messages)
        if truncated["truncated"]:
            attrs["new_context_truncated"] = True
            attrs["new_context_original_length"] = len(full_context)

    if system_reminders:
        full_reminders = "\n\n---\n\n".join(system_reminders)
        truncated = truncateContent(full_reminders)
        attrs["system_reminders"] = truncated["content"]
        attrs["system_reminders_count"] = len(system_reminders)
        if truncated["truncated"]:
            attrs["system_reminders_truncated"] = True
            attrs["system_reminders_original_length"] = len(full_reminders)

    _set_span_attributes(span, attrs)

    last_message = messagesForAPI[-1] if messagesForAPI else None
    if last_message is not None:
        lastReportedMessageHash[query_source] = hashMessage(last_message)


def addBetaLLMResponseAttributes(endAttributes, metadata=None):
    """Add beta attributes to endLLMRequestSpan."""
    if not isBetaTracingEnabled() or not metadata:
        return
    if metadata.get("modelOutput") is not None:
        truncated = truncateContent(metadata["modelOutput"])
        endAttributes["response.model_output"] = truncated["content"]
        if truncated["truncated"]:
            endAttributes["response.model_output_truncated"] = True
            endAttributes["response.model_output_original_length"] = len(metadata["modelOutput"])

    if os.environ.get("USER_TYPE") == "ant" and metadata.get("thinkingOutput") is not None:
        truncated = truncateContent(metadata["thinkingOutput"])
        endAttributes["response.thinking_output"] = truncated["content"]
        if truncated["truncated"]:
            endAttributes["response.thinking_output_truncated"] = True
            endAttributes["response.thinking_output_original_length"] = len(metadata["thinkingOutput"])


def addBetaToolInputAttributes(span, toolName, toolInput):
    """Add beta attributes to startToolSpan."""
    if not isBetaTracingEnabled():
        return
    truncated = truncateContent(f"[TOOL INPUT: {toolName}]\n{toolInput}")
    attrs = {"tool_input": truncated["content"]}
    if truncated["truncated"]:
        attrs["tool_input_truncated"] = True
        attrs["tool_input_original_length"] = len(toolInput)
    _set_span_attributes(span, attrs)


def addBetaToolResultAttributes(endAttributes, toolName, toolResult):
    """Add beta attributes to endToolSpan."""
    if not isBetaTracingEnabled():
        return
    truncated = truncateContent(f"[TOOL RESULT: {toolName}]\n{toolResult}")
    endAttributes["new_context"] = truncated["content"]
    if truncated["truncated"]:
        endAttributes["new_context_truncated"] = True
        endAttributes["new_context_original_length"] = len(toolResult)


clear_beta_tracing_state = clearBetaTracingState
is_beta_tracing_enabled = isBetaTracingEnabled
truncate_content = truncateContent
short_hash = shortHash
hash_system_prompt = hashSystemPrompt
hash_message = hashMessage
extract_system_reminder_content = extractSystemReminderContent
format_messages_for_context = formatMessagesForContext
add_beta_interaction_attributes = addBetaInteractionAttributes
add_beta_llm_request_attributes = addBetaLLMRequestAttributes
add_beta_llm_response_attributes = addBetaLLMResponseAttributes
add_beta_tool_input_attributes = addBetaToolInputAttributes
add_beta_tool_result_attributes = addBetaToolResultAttributes

